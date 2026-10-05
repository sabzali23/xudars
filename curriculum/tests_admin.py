"""Проверки панели управления: доступ, создание курса и защита от неверных заданий."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from curriculum.admin import QuestionForm
from curriculum.models import Material, Section, Topic


class AdminAccessTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(phone="+992900000010", password="test-pass-123", name="Админ")
        self.staff.is_staff = True
        self.staff.is_superuser = True
        self.staff.save()

    def test_admin_is_closed_for_anonymous(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_ordinary_parent_cannot_enter(self):
        parent = User.objects.create_user(phone="+992900000011", password="test-pass-123", name="Родитель")
        self.client.force_login(parent)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_open_course_list(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin:curriculum_section_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_create_course(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("admin:curriculum_section_add"),
            {"slug": "history", "title": "История", "description": "Пробный курс", "order": 4},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Section.objects.filter(slug="history", title="История").exists())


class MaterialRenderTests(TestCase):
    def test_html_is_rebuilt_from_markdown_on_save(self):
        """Правка конспекта в админке должна сразу попадать на сайт, а не оставлять старый HTML."""
        section = Section.objects.create(slug="math", title="Математика")
        topic = Topic.objects.create(section=section, slug="t1", title="Тема", order=1)
        material = Material.objects.create(topic=topic, summary_md="# Конспект", parent_guide_md="# Занятие")
        self.assertIn("<h1>Конспект</h1>", material.summary_html)
        self.assertIn("<h1>Занятие</h1>", material.parent_guide_html)

        material.summary_md = "## Новый заголовок"
        material.save()
        material.refresh_from_db()
        self.assertIn("<h2>Новый заголовок</h2>", material.summary_html)


class QuestionFormTests(TestCase):
    def setUp(self):
        section = Section.objects.create(slug="math", title="Математика")
        self.topic = Topic.objects.create(section=section, slug="t1", title="Тема", order=1)

    def form(self, options, correct):
        return QuestionForm(
            data={
                "topic": self.topic.pk,
                "pool": "entry",
                "order": 0,
                "text": "Сколько будет 2 + 2?",
                "options": options,
                "correct_index": correct,
                "explanation": "",
            }
        )

    def test_valid_question_accepted(self):
        self.assertTrue(self.form('["3", "4", "5"]', 1).is_valid())

    def test_correct_index_out_of_range_rejected(self):
        form = self.form('["3", "4"]', 5)
        self.assertFalse(form.is_valid())
        self.assertIn("correct_index", form.errors)

    def test_single_option_rejected(self):
        form = self.form('["4"]', 0)
        self.assertFalse(form.is_valid())
        self.assertIn("options", form.errors)
