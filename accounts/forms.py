from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.core.exceptions import ValidationError

from .models import PasswordResetRequest, User
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
        "inactive": "Ваш аккаунт не активирован. Свяжитесь с нами, и мы его включим.",
    }

    def clean(self):
        """Django отвечает одинаково на неверный пароль и на выключенный аккаунт — разбираем отдельно.

        О том, что аккаунт выключен, сообщаем только тому, кто ввёл верный пароль: иначе по ответу
        формы можно было бы перебором узнавать, какие номера зарегистрированы.
        """
        try:
            return super().clean()
        except ValidationError:
            phone = self.cleaned_data.get("username")
            password = self.cleaned_data.get("password")
            if phone and password:
                user = User.objects.filter(phone=phone).first()
                if user is not None and not user.is_active and user.check_password(password):
                    raise ValidationError(self.error_messages["inactive"], code="inactive")
            raise

    def clean_username(self):
        raw = self.cleaned_data["username"]
        try:
            return normalize_phone(raw)
        except ValidationError:
            return raw


class PasswordResetRequestForm(forms.Form):
    """Форма «забыли пароль»: родитель оставляет номер, по которому с ним свяжутся."""

    phone = forms.CharField(label="Телефон", widget=forms.TextInput(attrs={**PHONE_ATTRS, "autofocus": True}))

    def clean_phone(self):
        return normalize_phone(self.cleaned_data["phone"])

    def save(self):
        """Создаёт заявку, если такой номер зарегистрирован.

        Ответ страницы одинаков и для известного, и для незнакомого номера: иначе по форме можно
        было бы перебором узнать, какие телефоны есть в базе. Повторная заявка по тому же номеру
        не создаётся, пока прошлая не обработана, — иначе список заявок легко забить.
        """
        phone = self.cleaned_data["phone"]
        user = User.objects.filter(phone=phone).first()
        if user is None:
            return None
        existing = PasswordResetRequest.objects.filter(user=user, handled_at__isnull=True).first()
        return existing or PasswordResetRequest.objects.create(phone=phone, user=user)


class NewPasswordForm(SetPasswordForm):
    """Смена пароля по одноразовой ссылке."""

    new_password1 = forms.CharField(
        label="Новый пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "autofocus": True}),
        help_text="Не короче 6 символов.",
    )
    new_password2 = forms.CharField(
        label="Новый пароль ещё раз",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    error_messages = {**SetPasswordForm.error_messages, "password_mismatch": "Пароли не совпадают."}
