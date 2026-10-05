"""Учебный контент. Заполняется командой `load_content` из папки content/ или через админку."""

import markdown
from django.db import models


def render_markdown(text):
    """Markdown → HTML. Живёт здесь, чтобы загрузчик и админка рендерили одинаково."""
    return markdown.markdown(text, extensions=["extra", "sane_lists"])


class TestKind(models.TextChoices):
    ENTRY = "entry", "Входной тест"
    FINAL = "final", "Итоговый тест"


class Section(models.Model):
    """Раздел (предмет) — курс в каталоге."""

    slug = models.SlugField("адрес в ссылке", unique=True, help_text="Латиницей, например math или english")
    title = models.CharField("название", max_length=200)
    description = models.TextField("описание на карточке", blank=True, default="")
    order = models.PositiveIntegerField("порядок в каталоге", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "курс"
        verbose_name_plural = "курсы"

    def __str__(self):
        return self.title


class Topic(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="topics", verbose_name="курс")
    slug = models.SlugField("адрес в ссылке", unique=True, help_text="Латиницей, например simple-arithmetic")
    title = models.CharField("название темы", max_length=200)
    order = models.PositiveIntegerField("порядок в курсе", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "тема"
        verbose_name_plural = "темы"

    def __str__(self):
        return self.title


class Material(models.Model):
    topic = models.OneToOneField(Topic, on_delete=models.CASCADE, related_name="material", verbose_name="тема")
    video_url = models.URLField("ссылка на видео", blank=True, help_text="Необязательно")
    # Конспект обязателен: при слабом интернете он заменяет видео.
    summary_md = models.TextField("конспект (Markdown)", help_text="Обязателен: при слабом интернете он заменяет видео")
    summary_html = models.TextField("конспект в HTML", blank=True)
    # Руководство «как провести занятие» обязательно: в v1 занятие ведёт родитель, а не преподаватель.
    parent_guide_md = models.TextField(
        "как провести занятие (Markdown)",
        help_text="Обязательно: сценарий для родителя — что сказать, о чём спросить, что делать при ошибке",
    )
    parent_guide_html = models.TextField("сценарий в HTML", blank=True)

    class Meta:
        verbose_name = "материал"
        verbose_name_plural = "материалы"
        constraints = [
            models.CheckConstraint(condition=~models.Q(summary_md=""), name="material_summary_required"),
            models.CheckConstraint(condition=~models.Q(parent_guide_md=""), name="material_parent_guide_required"),
        ]

    def save(self, *args, **kwargs):
        # HTML всегда пересобирается из Markdown: иначе правка через админку осталась бы невидимой на сайте.
        self.summary_html = render_markdown(self.summary_md)
        self.parent_guide_html = render_markdown(self.parent_guide_md)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Материал: {self.topic}"


class Question(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions", verbose_name="тема")
    # Пулы входного и итогового теста не пересекаются.
    pool = models.CharField("тест", max_length=10, choices=TestKind.choices)
    order = models.PositiveIntegerField("порядок в тесте")
    text = models.TextField("текст задания")
    options = models.JSONField("варианты ответа", help_text='Список в кавычках, например: ["9", "10", "11"]')
    correct_index = models.PositiveSmallIntegerField(
        "номер правильного варианта", help_text="Считается с нуля: первый вариант — 0, второй — 1"
    )
    explanation = models.TextField("объяснение", blank=True, help_text="Показывается в разборе ошибок")

    class Meta:
        ordering = ["topic", "pool", "order"]
        verbose_name = "задание"
        verbose_name_plural = "задания"
        constraints = [
            models.UniqueConstraint(fields=["topic", "pool", "order"], name="question_unique_order_in_pool"),
        ]

    def __str__(self):
        return self.text[:60]
