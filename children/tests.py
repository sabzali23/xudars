from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from curriculum.testing import make_child, make_topic

from .models import Child


class ProfileTests(TestCase):
    def setUp(self):
        self.child = make_child()
        self.parent = self.child.user
        self.parent.telegram = "@sabzali"
        self.parent.save()
        self.topic = make_topic()
        self.client.force_login(self.parent)
        self.url = reverse("child_profile")

    def test_profile_shows_parent_data(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.parent.name)
        self.assertContains(response, self.parent.phone)
        self.assertContains(response, "@sabzali")

    def test_profile_shows_child_data(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.child.name)
        self.assertContains(response, self.child.get_grade_display())
        self.assertContains(response, self.child.target_school)

    def test_profile_shows_progress_per_course(self):
        response = self.client.get(self.url)
        course = response.context["rows"][0]["sections"][0]
        self.assertEqual((course["section"], course["total"], course["passed"]), (self.topic.section, 1, 0))

    def test_parent_without_child_sees_creation_form(self):
        user = User.objects.create_user(phone="+992900000055", password="test-pass-123", name="Новый родитель")
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertTrue(response.context["is_new"])
        self.assertContains(response, "Шаг 2 из 2")

    def test_editing_child_saves_and_returns_to_profile(self):
        response = self.client.post(
            reverse("child_edit", args=[self.child.pk]),
            {"name": "Зокия", "grade": 2, "target_school": "Школа №2"},
        )
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.child.refresh_from_db()
        self.assertEqual((self.child.name, self.child.grade, self.child.target_school), ("Зокия", 2, "Школа №2"))


class SeveralChildrenTests(TestCase):
    def setUp(self):
        self.first = make_child()
        self.parent = self.first.user
        self.topic = make_topic()
        self.client.force_login(self.parent)

    def add_second(self, name="Далер", grade=2):
        return self.client.post(
            reverse("child_add"), {"name": name, "grade": grade, "target_school": "Школа №1"}
        )

    def test_second_child_is_added_and_becomes_active(self):
        response = self.add_second()
        self.assertRedirects(response, reverse("child_profile"), fetch_redirect_response=False)
        self.assertEqual(Child.objects.filter(user=self.parent).count(), 2)

        # Новый ребёнок сразу становится активным — его имя показывает каталог.
        catalog = self.client.get(reverse("home"))
        self.assertEqual(catalog.context["request"].child.name, "Далер")

    def test_profile_lists_both_children(self):
        self.add_second()
        response = self.client.get(reverse("child_profile"))
        names = [row["child"].name for row in response.context["rows"]]
        self.assertEqual(names, [self.first.name, "Далер"])
        self.assertEqual([row["is_active"] for row in response.context["rows"]], [False, True])

    def test_switching_back_changes_active_child(self):
        self.add_second()
        response = self.client.post(reverse("child_switch", args=[self.first.pk]))
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        catalog = self.client.get(reverse("home"))
        self.assertEqual(catalog.context["request"].child, self.first)

    def test_progress_of_children_does_not_mix(self):
        """Тест, пройденный одним ребёнком, не должен появляться у второго."""
        self.add_second()  # активен второй ребёнок
        url = reverse("topic_test", args=[self.topic.slug, "entry"])
        question = self.client.get(url).context["question"]
        self.client.post(url, {"question_id": question.pk, "answer": question.correct_index})

        second = Child.objects.get(user=self.parent, name="Далер")
        self.assertTrue(second.attempts.exists())
        self.assertFalse(self.first.attempts.exists())

    def test_cannot_switch_to_another_parents_child(self):
        stranger = make_child(phone="+992900000002")
        response = self.client.post(reverse("child_switch", args=[stranger.pk]))
        self.assertEqual(response.status_code, 404)

    def test_cannot_edit_another_parents_child(self):
        stranger = make_child(phone="+992900000003")
        self.assertEqual(self.client.get(reverse("child_edit", args=[stranger.pk])).status_code, 404)
