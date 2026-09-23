from django.db import models

from children.models import Child
from curriculum.models import TestKind, Topic


class TopicStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Не начата"
    IN_PROGRESS = "in_progress", "В процессе"
    PASSED = "passed", "Пройдена"
    NEEDS_REPEAT = "needs_repeat", "Нужно повторить"


class Stage(models.TextChoices):
    """Шаг цикла по теме. Шаги нельзя пропускать."""

    ENTRY_TEST = "entry_test", "Входной тест"
    MATERIAL = "material", "Материал"
    FINAL_TEST = "final_test", "Итоговый тест"
    DONE = "done", "Цикл завершён"


class TopicProgress(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="progress")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="progress")
    status = models.CharField(max_length=20, choices=TopicStatus.choices, default=TopicStatus.NOT_STARTED)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.ENTRY_TEST)
    entry_score = models.PositiveSmallIntegerField(null=True, blank=True)
    last_score = models.PositiveSmallIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["child", "topic"], name="progress_unique_child_topic"),
        ]

    def __str__(self):
        return f"{self.child} — {self.topic}: {self.get_status_display()}"


class TestAttempt(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="attempts")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="attempts")
    kind = models.CharField(max_length=10, choices=TestKind.choices)
    # Задания выбираются при старте и не меняются, чтобы тест можно было продолжить после перерыва.
    question_ids = models.JSONField(default=list)
    # {"<id задания>": номер выбранного варианта}; сохраняется после каждого ответа.
    answers = models.JSONField(default=dict, blank=True)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]

    def __str__(self):
        return f"{self.child} — {self.topic}: {self.get_kind_display()}"

    @property
    def is_finished(self):
        return self.finished_at is not None
