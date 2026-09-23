from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import PhoneLoginForm, SignupForm


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
