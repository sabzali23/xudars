from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, PasswordResetConfirmView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import NewPasswordForm, PasswordResetRequestForm, PhoneLoginForm, SignupForm
from .models import PasswordResetRequest


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("child_profile")
    return render(request, "accounts/signup.html", {"form": form})


class PhoneLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = PhoneLoginForm
    redirect_authenticated_user = True


def password_reset_request(request):
    """Заявка «забыл пароль»: родитель оставляет номер, дальше с ним связываются вручную."""
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("password_reset_sent")
    return render(request, "accounts/password_reset.html", {"form": form})


def password_reset_sent(request):
    return render(request, "accounts/password_reset_sent.html")


class PhonePasswordResetConfirmView(PasswordResetConfirmView):
    """Смена пароля по одноразовой ссылке, которую владелец платформы выдал после звонка."""

    template_name = "accounts/password_reset_confirm.html"
    form_class = NewPasswordForm
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        response = super().form_valid(form)
        PasswordResetRequest.objects.filter(user=self.user, handled_at__isnull=True).update(
            handled_at=timezone.now()
        )
        messages.success(self.request, "Пароль изменён. Войдите с новым паролем.")
        return response
