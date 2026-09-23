from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import User
from accounts.phone import normalize_phone
from children.models import Child

PASSWORD = "secret-pass-1"


class NormalizePhoneTests(SimpleTestCase):
    def test_local_number_gets_tajikistan_code(self):
        self.assertEqual(normalize_phone("93 123 45 67"), "+992931234567")

    def test_formatting_is_removed(self):
        self.assertEqual(normalize_phone("+992 (93) 123-45-67"), "+992931234567")

    def test_too_short_number_rejected(self):
        with self.assertRaises(ValidationError):
            normalize_phone("12345")


class SignupAndLoginTests(TestCase):
    def signup(self, phone="93 123 45 67"):
        return self.client.post(
            reverse("signup"),
            {"name": "Мадина", "phone": phone, "telegram": "", "password1": PASSWORD, "password2": PASSWORD},
        )

    def test_signup_logs_in_and_asks_for_child_profile(self):
        response = self.signup()
        self.assertRedirects(response, reverse("child_profile"))
        user = User.objects.get()
        self.assertEqual(user.phone, "+992931234567")
        self.assertTrue(user.check_password(PASSWORD))

    def test_duplicate_phone_in_other_format_rejected(self):
        User.objects.create_user(phone="+992931234567", password=PASSWORD, name="Мадина")
        response = self.signup(phone="+992 93 123-45-67")
        self.assertEqual(response.status_code, 200)
        self.assertIn("phone", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_login_accepts_phone_in_any_format(self):
        User.objects.create_user(phone="+992931234567", password=PASSWORD, name="Мадина")
        response = self.client.post(reverse("login"), {"username": "93-123-45-67", "password": PASSWORD})
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)

    def test_child_profile_is_created_for_current_parent(self):
        self.signup()
        response = self.client.post(
            reverse("child_add"), {"name": "Али", "grade": 4, "target_school": "Школа №1"}
        )
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(Child.objects.get().user, User.objects.get())

    def test_home_without_child_profile_redirects_to_profile(self):
        user = User.objects.create_user(phone="+992931234567", password=PASSWORD, name="Мадина")
        self.client.force_login(user)
        self.assertRedirects(self.client.get(reverse("home")), reverse("child_profile"))
