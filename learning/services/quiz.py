"""Тесты: выбор заданий, сохранение ответов, подсчёт балла и разбор ошибок."""

from collections import Counter

from django.conf import settings
from django.utils import timezone

from curriculum.models import Question, TestKind
from learning.models import TestAttempt
from learning.services import progress as progress_service


def select_questions(child, topic, kind):
    """Входной тест берёт задания только из пула entry, итоговый — только из final.

    При повторе итогового теста сначала идут задания, которые ребёнок ещё не решал,
    затем — решавшиеся реже всего.
    """
    pool = list(Question.objects.filter(topic=topic, pool=kind).order_by("order").values_list("pk", flat=True))
    if kind == TestKind.FINAL:
        seen = Counter()
        previous = TestAttempt.objects.filter(child=child, topic=topic, kind=TestKind.FINAL)
        for ids in previous.values_list("question_ids", flat=True):
            seen.update(ids)
        pool.sort(key=lambda pk: seen[pk])  # сортировка устойчивая: внутри группы сохраняется порядок из контента
    return pool[: settings.TEST_SIZE]


def get_or_start_attempt(child, topic, kind):
    attempt = TestAttempt.objects.filter(child=child, topic=topic, kind=kind, finished_at__isnull=True).first()
    if attempt is None:
        attempt = TestAttempt.objects.create(
            child=child, topic=topic, kind=kind, question_ids=select_questions(child, topic, kind)
        )
        progress_service.on_test_started(child, topic)
    return attempt


def _existing_ids(attempt):
    """Задания попытки, которые всё ещё есть в базе (контент мог обновиться)."""
    existing = set(Question.objects.filter(pk__in=attempt.question_ids).values_list("pk", flat=True))
    return [pk for pk in attempt.question_ids if pk in existing]


def current_question(attempt):
    for pk in _existing_ids(attempt):
        if str(pk) not in attempt.answers:
            return Question.objects.get(pk=pk)
    return None


def position(attempt):
    """(номер текущего задания, всего заданий)."""
    ids = _existing_ids(attempt)
    answered = sum(1 for pk in ids if str(pk) in attempt.answers)
    return min(answered + 1, len(ids)), len(ids)


def record_answer(attempt, question, index):
    """Сохраняет ответ. Возвращает True, если это был последний вопрос и тест завершён."""
    attempt.answers[str(question.pk)] = index
    attempt.save(update_fields=["answers"])
    if current_question(attempt) is None:
        finish_attempt(attempt)
        return True
    return False


def review(attempt):
    questions = Question.objects.in_bulk(attempt.question_ids)
    items = []
    for pk in attempt.question_ids:
        question = questions.get(pk)
        if question is None:
            continue
        chosen = attempt.answers.get(str(pk))
        chosen_valid = isinstance(chosen, int) and 0 <= chosen < len(question.options)
        items.append(
            {
                "question": question,
                "chosen_text": question.options[chosen] if chosen_valid else "—",
                "correct_text": question.options[question.correct_index],
                "is_correct": chosen == question.correct_index,
            }
        )
    return items


def finish_attempt(attempt):
    items = review(attempt)
    correct = sum(1 for item in items if item["is_correct"])
    attempt.score = round(100 * correct / len(items)) if items else 0
    attempt.finished_at = timezone.now()
    attempt.save(update_fields=["score", "finished_at"])
    progress_service.on_attempt_finished(attempt)
