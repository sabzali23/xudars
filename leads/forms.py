from django import forms

from accounts.phone import normalize_phone

from .models import ConsultationRequest

GRADE_CHOICES = [("", "Класс")] + [(i, f"{i} класс") for i in range(1, 12)]


class ConsultationForm(forms.ModelForm):
    """Короткая форма с лендинга: имя, класс, телефон."""

    class Meta:
        model = ConsultationRequest
        fields = ["name", "grade", "phone"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Имя", "autocomplete": "name", "maxlength": 100}),
            "phone": forms.TextInput(
                attrs={"type": "tel", "placeholder": "+992 93 123 45 67", "autocomplete": "tel"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Вместо «---------» в пустом варианте — понятная подпись «Класс», как placeholder у остальных полей.
        self.fields["grade"].choices = GRADE_CHOICES

    def clean_phone(self):
        """Приводим номер к виду +992…, как и при регистрации родителя."""
        return normalize_phone(self.cleaned_data["phone"])
