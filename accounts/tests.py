from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import PasswordResetRequest, User
from accounts.phone import normalize_phone
from accounts.reset import reset_path
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

    def test_inactive_account_gets_a_clear_message(self):
        user = User.objects.create_user(phone="+992931234567", password=PASSWORD, name="Мадина")
        user.is_active = False
        user.save()
        response = self.client.post(reverse("login"), {"username": "+992931234567", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "не активирован")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_wrong_password_does_not_reveal_that_account_exists(self):
        """Иначе по ответу формы можно было бы перебором искать зарегистрированные номера."""
        user = User.objects.create_user(phone="+992931234567", password=PASSWORD, name="Мадина")
        user.is_active = False
        user.save()
        response = self.client.post(reverse("login"), {"username": "+992931234567", "password": "another-pass-7"})
        self.assertContains(response, "Неверный телефон или пароль")
        self.assertNotContains(response, "не активирован")

    def test_deactivated_user_loses_access_immediately(self):
        user = User.objects.create_user(phone="+992931234567", password=PASSWORD, name="Мадина")
        self.client.force_login(user)
        user.is_active = False
        user.save()
        response = self.client.get(reverse("progress"))
        self.assertEqual(response.status_code, 302)

    def test_home_without_child_profile_redirects_to_profile(self):
        user = User.objects.create_user(phone="+992931234567", password=PASSWORD, name="Мадина")
        self.client.force_login(user)
        self.assertRedirects(self.client.get(reverse("home")), reverse("child_profile"))


class PasswordResetTests(TestCase):
    """Пароль восстанавливается через человека: заявка → звонок → одноразовая ссылка."""

    def setUp(self):
        self.user = User.objects.create_user(phone="+992931234567", password=PASSWORD, name="Мадина")

    def request_reset(self, phone):
        return self.client.post(reverse("password_reset"), {"phone": phone})

    def test_request_creates_a_row_for_a_known_phone(self):
        self.assertRedirects(self.request_reset("93-123-45-67"), reverse("password_reset_sent"))
        row = PasswordResetRequest.objects.get()
        self.assertEqual(row.user, self.user)
        self.assertIsNone(row.handled_at)

    def test_unknown_phone_gets_the_same_answer_and_creates_nothing(self):
        """Иначе по ответу формы можно было бы перебором искать зарегистрированные номера."""
        known = self.request_reset("+992931234567")
        unknown = self.request_reset("+992900000001")
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.url, unknown.url)
        self.assertEqual(PasswordResetRequest.objects.filter(user=None).count(), 0)

    def test_repeated_request_does_not_pile_up(self):
        self.request_reset("+992931234567")
        self.request_reset("+992931234567")
        self.assertEqual(PasswordResetRequest.objects.count(), 1)

    def test_link_lets_the_parent_set_a_new_password(self):
        self.request_reset("+992931234567")
        # Django сначала прячет токен в сессию и перенаправляет на страницу с формой.
        page = self.client.get(reset_path(self.user), follow=True)
        self.assertTrue(page.context["validlink"])
        response = self.client.post(
            page.request["PATH_INFO"], {"new_password1": "new-pass-9", "new_password2": "new-pass-9"}
        )
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-pass-9"))
        self.assertIsNotNone(PasswordResetRequest.objects.get().handled_at)

    def test_link_stops_working_after_the_password_is_changed(self):
        """В токен входит хеш пароля, поэтому старая ссылка гаснет сама."""
        path = reset_path(self.user)
        page = self.client.get(path, follow=True)
        self.client.post(page.request["PATH_INFO"], {"new_password1": "new-pass-9", "new_password2": "new-pass-9"})
        again = self.client.get(path, follow=True)
        self.assertFalse(again.context["validlink"])

    def test_login_page_offers_the_link(self):
        self.assertContains(self.client.get(reverse("login")), reverse("password_reset"))
