"""Порядок шагов по теме и переходы статусов. Все проверки доступа к шагам цикла живут здесь."""

from django.conf import settings
from django.urls import reverse

from curriculum.models import TestKind
from learning.models import Stage, TestAttempt, TopicProgress, TopicStatus


def get_progress(child, topic):
    """Прогресс по теме; если ребёнок тему ещё не открывал — несохранённый объект со значениями по умолчанию."""
    return TopicProgress.objects.filter(child=child, topic=topic).first() or TopicProgress(child=child, topic=topic)


def ensure_progress(child, topic):
    progress, _ = TopicProgress.objects.get_or_create(child=child, topic=topic)
    return progress


def has_finished_entry(child, topic):
    return TestAttempt.objects.filter(
        child=child, topic=topic, kind=TestKind.ENTRY, finished_at__isnull=False
    ).exists()


def can_open_material(progress):
    """Материал открывается только после прохождения входного теста."""
    return has_finished_entry(progress.child, progress.topic)


def current_stage(progress):
    """Шаг, на котором находится ребёнок. Без пройденного входного теста — всегда входной тест."""
    if progress.stage != Stage.ENTRY_TEST and not has_finished_entry(progress.child, progress.topic):
        return Stage.ENTRY_TEST
    return progress.stage


def step_url(progress):
    slug = progress.topic.slug
    stage = current_stage(progress)
    if stage == Stage.ENTRY_TEST:
        return reverse("topic_test", args=[slug, TestKind.ENTRY])
    if stage == Stage.MATERIAL:
        return reverse("topic_material", args=[slug])
    if stage == Stage.FINAL_TEST:
        return reverse("topic_test", args=[slug, TestKind.FINAL])
    return reverse("topic_next", args=[slug])


def on_test_started(child, topic):
    progress = ensure_progress(child, topic)
    if progress.status != TopicStatus.IN_PROGRESS:
        progress.status = TopicStatus.IN_PROGRESS
        progress.save()


def on_attempt_finished(attempt):
    progress = ensure_progress(attempt.child, attempt.topic)
    progress.last_score = attempt.score
    if attempt.kind == TestKind.ENTRY:
        progress.entry_score = attempt.score
        progress.stage = Stage.MATERIAL
        progress.status = TopicStatus.IN_PROGRESS
    else:
        progress.stage = Stage.DONE
        passed = attempt.score >= settings.PASS_THRESHOLD
        progress.status = TopicStatus.PASSED if passed else TopicStatus.NEEDS_REPEAT
    progress.save()


def mark_material_opened(progress):
    """После открытия материала становится доступен итоговый тест."""
    if progress.pk and current_stage(progress) == Stage.MATERIAL:
        progress.stage = Stage.FINAL_TEST
        progress.save()


def start_repeat(progress):
    """Повтор завершённой темы: снова материал, затем итоговый тест с новыми заданиями."""
    if progress.pk and current_stage(progress) == Stage.DONE:
        progress.stage = Stage.MATERIAL
        progress.status = TopicStatus.IN_PROGRESS
        progress.save()
