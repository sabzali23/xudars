"""Панель управления учебным контентом.

Через неё курсы и темы можно добавлять руками, не трогая файлы в content/.
Поля с HTML скрыты: они пересобираются из Markdown при сохранении.
"""

from django import forms
from django.contrib import admin

from .models import Material, Question, Section, Topic


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = "__all__"

    def clean(self):
        """Те же проверки, что и у загрузчика файлов: иначе через админку можно сломать тест."""
        cleaned = super().clean()
        options = cleaned.get("options")
        correct = cleaned.get("correct_index")
        if not isinstance(options, list) or len(options) < 2 or not all(isinstance(o, str) and o.strip() for o in options):
            self.add_error("options", 'Нужен список минимум из двух непустых вариантов, например: ["9", "10", "11"]')
        elif correct is not None and not 0 <= correct < len(options):
            self.add_error("correct_index", f"Номер правильного ответа считается с нуля: от 0 до {len(options) - 1}")
        return cleaned


class MaterialInline(admin.StackedInline):
    model = Material
    can_delete = False
    extra = 0
    fields = ("video_url", "summary_md", "parent_guide_md")
    verbose_name_plural = "Материал темы (конспект обязателен)"


class QuestionInline(admin.TabularInline):
    model = Question
    form = QuestionForm
    extra = 0
    fields = ("pool", "order", "text", "options", "correct_index", "explanation")
    ordering = ("pool", "order")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "order", "topic_count")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "slug")

    @admin.display(description="Тем в курсе")
    def topic_count(self, section):
        return section.topics.count()


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "order", "slug", "entry_count", "final_count", "has_material")
    list_filter = ("section",)
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "slug")
    inlines = [MaterialInline, QuestionInline]

    @admin.display(description="Входной тест")
    def entry_count(self, topic):
        return topic.questions.filter(pool="entry").count()

    @admin.display(description="Итоговый тест")
    def final_count(self, topic):
        return topic.questions.filter(pool="final").count()

    @admin.display(description="Материал", boolean=True)
    def has_material(self, topic):
        return hasattr(topic, "material")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionForm
    list_display = ("short_text", "topic", "pool", "order")
    list_filter = ("pool", "topic__section", "topic")
    search_fields = ("text",)

    @admin.display(description="Задание")
    def short_text(self, question):
        return question.text[:80]
