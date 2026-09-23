from django.test import TestCase
from django.urls import reverse

from .models import ConsultationRequest


class ConsultationRequestTests(TestCase):
    def setUp(self):
        self.url = reverse("consultation")
        self.valid = {"name": "Сабзали", "grade": 1, "phone": "931234567"}

    def test_guest_sees_form_on_landing(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, self.url)
        self.assertContains(response, "Хочу консультацию")

    def test_request_is_saved_and_phone_normalized(self):
        response = self.client.post(self.url, self.valid)
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        lead = ConsultationRequest.objects.get()
        self.assertEqual((lead.name, lead.grade, lead.phone), ("Сабзали", 1, "+992931234567"))
        self.assertIsNone(lead.handled_at)

    def test_bad_phone_returns_landing_with_error_and_saves_nothing(self):
        response = self.client.post(self.url, {**self.valid, "phone": "123"})
        self.assertTemplateUsed(response, "landing.html")
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(ConsultationRequest.objects.exists())

    def test_grade_is_required(self):
        response = self.client.post(self.url, {**self.valid, "grade": ""})
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(ConsultationRequest.objects.exists())

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
