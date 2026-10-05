from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.PhoneLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password-reset/", views.password_reset_request, name="password_reset"),
    path("password-reset/sent/", views.password_reset_sent, name="password_reset_sent"),
    path(
        "password-reset/<uidb64>/<token>/",
        views.PhonePasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
]
