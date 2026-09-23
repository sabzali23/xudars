from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.PhoneLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
