"""Учебный контент. Заполняется командой `load_content` из папки content/, а не через интерфейс."""

from django.db import models


class TestKind(models.TextChoices):
    ENTRY = "entry", "Входной тест"
    FINAL = "final", "Итоговый тест"


class Section(models.Model):
    """Раздел (предмет) — курс в каталоге."""

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Topic(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="topics")
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Material(models.Model):
    topic = models.OneToOneField(Topic, on_delete=models.CASCADE, related_name="material")
    video_url = models.URLField(blank=True)
    # Конспект обязателен: при слабом интернете он заменяет видео.
    summary_md = models.TextField()
    summary_html = models.TextField()
    # Руководство «как провести занятие» обязательно: в v1 занятие ведёт родитель, а не преподаватель.
    parent_guide_md = models.TextField()
    parent_guide_html = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~models.Q(summary_md=""), name="material_summary_required"),
            models.CheckConstraint(condition=~models.Q(parent_guide_md=""), name="material_parent_guide_required"),
        ]

    def __str__(self):
        return f"Материал: {self.topic}"


class Question(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions")
    # Пулы входного и итогового теста не пересекаются.
    pool = models.CharField(max_length=10, choices=TestKind.choices)
    order = models.PositiveIntegerField()
    text = models.TextField()
    options = models.JSONField()
    correct_index = models.PositiveSmallIntegerField()
    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ["topic", "pool", "order"]
        constraints = [
            models.UniqueConstraint(fields=["topic", "pool", "order"], name="question_unique_order_in_pool"),
        ]

    def __str__(self):
        return self.text[:60]
