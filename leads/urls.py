from django.urls import path

from . import views

urlpatterns = [
    path("consultation/", views.consultation, name="consultation"),
]
