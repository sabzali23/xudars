from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .models import User
from .phone import normalize_phone

PHONE_ATTRS = {"type": "tel", "autocomplete": "tel", "placeholder": "+992 93 123 45 67"}


class SignupForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Не короче 6 символов.",
    )
    password2 = forms.CharField(
        label="Пароль ещё раз",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["name", "phone", "telegram"]
        widgets = {"phone": forms.TextInput(attrs=PHONE_ATTRS)}

    def clean_phone(self):
        return normalize_phone(self.cleaned_data["phone"])

    def clean(self):
        cleaned = super().clean()
        password1, password2 = cleaned.get("password1"), cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Пароли не совпадают.")
        return cleaned

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get("password1")
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error("password1", error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class PhoneLoginForm(AuthenticationForm):
    username = forms.CharField(label="Телефон", widget=forms.TextInput(attrs={**PHONE_ATTRS, "autofocus": True}))

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Неверный телефон или пароль.",
    }

    def clean_username(self):
        raw = self.cleaned_data["username"]
        try:
            return normalize_phone(raw)
        except ValidationError:
            return raw
