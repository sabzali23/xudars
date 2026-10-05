from django import forms

from accounts.phone import normalize_phone

from .models import ConsultationRequest


class ConsultationForm(forms.ModelForm):
    """Короткая форма с лендинга: имя и телефон.

    Класс ребёнка здесь не спрашиваем — чем короче форма, тем больше заявок доходит до конца;
    всё остальное выясняется на самой консультации.
    """

    class Meta:
        model = ConsultationRequest
        fields = ["name", "phone"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Имя", "autocomplete": "name", "maxlength": 100}),
            "phone": forms.TextInput(
                attrs={"type": "tel", "placeholder": "+992 93 123 45 67", "autocomplete": "tel"}
            ),
        }

    def clean_phone(self):
        """Приводим номер к виду +992…, как и при регистрации родителя."""
        return normalize_phone(self.cleaned_data["phone"])
