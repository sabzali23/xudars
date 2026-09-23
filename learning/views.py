from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from children.decorators import child_required
from curriculum.models import Material, Section, TestKind, Topic
from leads.forms import ConsultationForm

from .models import Stage, TestAttempt, TopicProgress, TopicStatus
from .services import progress as progress_service
from .services import quiz
from .services.recommendation import recommend_topic


def _sections_with_progress(child):
    progress_by_topic = {p.topic_id: p for p in TopicProgress.objects.filter(child=child)}
    sections = []
    for section in Section.objects.prefetch_related("topics"):
        rows = [(topic, progress_by_topic.get(topic.pk)) for topic in section.topics.all()]
        passed = sum(1 for _, p in rows if p and p.status == TopicStatus.PASSED)
        scored = [p.last_score for _, p in rows if p and p.last_score is not None]
        sections.append(
            {
                "section": section,
                "rows": rows,
                "passed": passed,
                "total": len(rows),
                "left": len(rows) - passed,
                "percent": round(100 * passed / len(rows)) if rows else 0,
                "average": round(sum(scored) / len(scored)) if scored else None,
                "started": any(p is not None for _, p in rows),
                "recommended": recommend_topic(child, section=section),
            }
        )
    return sections, progress_by_topic


def landing_context(form=None):
    """Контекст лендинга. Форма заявки приходит заполненной, когда её нужно показать с ошибками."""
    # Гостю показываем и названия модулей курса — внутрь пускаем только после входа.
    courses = [
        {"section": section, "topics": list(section.topics.order_by("order"))}
        for section in Section.objects.prefetch_related("topics")
    ]
    return {
        "courses": courses,
        "coming_soon": settings.COMING_SOON_COURSES,
        "stories": settings.STUDENT_STORIES,
        "form": form or ConsultationForm(),
    }


def home(request):
    """Гостю — лендинг, родителю — каталог курсов."""
    if not request.user.is_authenticated:
        return render(request, "landing.html", landing_context())
    return catalog(request)


@child_required
def catalog(request):
    sections, _ = _sections_with_progress(request.child)
    return render(
        request, "learning/catalog.html", {"sections": sections, "coming_soon": settings.COMING_SOON_COURSES}
    )


def course(request, slug):
    """Программа курса открыта всем: гость видит список модулей, но не то, что внутри."""
    if not request.user.is_authenticated:
        section = get_object_or_404(Section, slug=slug)
        return render(
            request,
            "learning/course_public.html",
            {"section": section, "topics": list(section.topics.order_by("order"))},
        )
    return _course_for_parent(request, slug)


@child_required
def _course_for_parent(request, slug):
    sections, progress_by_topic = _sections_with_progress(request.child)
    course_data = next((s for s in sections if s["section"].slug == slug), None)
    if course_data is None:
        raise Http404("Курс не найден.")
    recommended = course_data["recommended"]
    return render(
        request,
        "learning/course.html",
        {
            "s": course_data,
            "recommended": recommended,
            "recommended_progress": progress_by_topic.get(recommended.pk) if recommended else None,
        },
    )


@child_required
def progress_overview(request):
    sections, progress_by_topic = _sections_with_progress(request.child)
    weak = sorted(
        (p for p in progress_by_topic.values() if p.last_score is not None),
        key=lambda p: (p.last_score, p.topic.order),
    )
    return render(
        request,
        "learning/progress.html",
        {"sections": sections, "weak": weak, "threshold": settings.PASS_THRESHOLD},
    )


@child_required
def topic_router(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    return redirect(progress_service.step_url(progress_service.get_progress(request.child, topic)))


@child_required
def take_test(request, slug, kind):
    child = request.child
    topic = get_object_or_404(Topic, slug=slug)
    progress = progress_service.get_progress(child, topic)
    expected_stage = Stage.ENTRY_TEST if kind == TestKind.ENTRY else Stage.FINAL_TEST
    if progress_service.current_stage(progress) != expected_stage:
        return redirect(progress_service.step_url(progress))

    attempt = quiz.get_or_start_attempt(child, topic, kind)
    question = quiz.current_question(attempt)
    if question is None:
        quiz.finish_attempt(attempt)
        return _after_finish(request, attempt)

    error = None
    if request.method == "POST":
        if request.POST.get("question_id") != str(question.pk):
            # Повторная отправка уже сохранённого ответа (например, при обрыве связи).
            return redirect(request.path)
        try:
            index = int(request.POST.get("answer", ""))
        except ValueError:
            index = -1
        if 0 <= index < len(question.options):
            if quiz.record_answer(attempt, question, index):
                return _after_finish(request, attempt)
            return redirect(request.path)
        error = "Выберите один вариант ответа."

    number, total = quiz.position(attempt)
    return render(
        request,
        "learning/test_question.html",
        {
            "topic": topic,
            "kind": kind,
            "kind_label": TestKind(kind).label,
            "question": question,
            "options": list(enumerate(question.options)),
            "number": number,
            "done": number - 1,
            "total": total,
            "error": error,
        },
    )


def _after_finish(request, attempt):
    if attempt.kind == TestKind.ENTRY:
        messages.success(
            request, f"Входной тест пройден: {attempt.score}%. Теперь изучите материал по теме."
        )
        return redirect("topic_material", attempt.topic.slug)
    return redirect("topic_result", attempt.topic.slug, attempt.pk)


@child_required
def material(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    progress = progress_service.get_progress(request.child, topic)
    if not progress_service.can_open_material(progress):
        messages.info(request, "Сначала пройдите входной тест — так мы поймём, на что обратить внимание.")
        return redirect("topic_test", slug, TestKind.ENTRY)
    material_obj = Material.objects.filter(topic=topic).first()
    if material_obj is None:
        raise Http404("Материал по теме ещё не добавлен.")
    progress_service.mark_material_opened(progress)
    return render(
        request,
        "learning/material.html",
        {"topic": topic, "material": material_obj, "progress": progress},
    )


@child_required
def result(request, slug, attempt_id):
    attempt = get_object_or_404(
        TestAttempt, pk=attempt_id, child=request.child, topic__slug=slug, finished_at__isnull=False
    )
    topic = attempt.topic
    finished = TestAttempt.objects.filter(child=request.child, topic=topic, finished_at__isnull=False)

    before, before_label = None, ""
    if attempt.kind == TestKind.FINAL:
        previous_final = (
            finished.filter(kind=TestKind.FINAL, finished_at__lt=attempt.finished_at).order_by("-finished_at").first()
        )
        entry = finished.filter(kind=TestKind.ENTRY).order_by("finished_at").first()
        if previous_final:
            before, before_label = previous_final.score, "Прошлая попытка"
        elif entry:
            before, before_label = entry.score, "Входной тест"

    items = quiz.review(attempt)
    correct = sum(1 for item in items if item["is_correct"])
    return render(
        request,
        "learning/result.html",
        {
            "topic": topic,
            "attempt": attempt,
            "before": before,
            "before_label": before_label,
            "delta": attempt.score - before if before is not None else None,
            "passed": attempt.score >= settings.PASS_THRESHOLD,
            "threshold": settings.PASS_THRESHOLD,
            "mistakes": [item for item in items if not item["is_correct"]],
            "correct": correct,
            "total": len(items),
        },
    )


@child_required
def next_step(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    progress = progress_service.get_progress(request.child, topic)
    if progress_service.current_stage(progress) != Stage.DONE:
        return redirect(progress_service.step_url(progress))

    next_topic = next_progress = None
    if progress.status == TopicStatus.PASSED:
        next_topic = recommend_topic(request.child, exclude=topic, section=topic.section)
        if next_topic:
            next_progress = TopicProgress.objects.filter(child=request.child, topic=next_topic).first()
    last_final = (
        TestAttempt.objects.filter(child=request.child, topic=topic, kind=TestKind.FINAL, finished_at__isnull=False)
        .order_by("-finished_at")
        .first()
    )
    return render(
        request,
        "learning/next.html",
        {
            "topic": topic,
            "progress": progress,
            "next_topic": next_topic,
            "next_is_review": bool(next_progress and next_progress.status == TopicStatus.PASSED),
            "last_final": last_final,
            "threshold": settings.PASS_THRESHOLD,
        },
    )


@require_POST
@child_required
def repeat(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    progress = progress_service.get_progress(request.child, topic)
    progress_service.start_repeat(progress)
    return redirect(progress_service.step_url(progress))
