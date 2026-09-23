from django.urls import path

from . import views

urlpatterns = [
    path("child/", views.child_profile, name="child_profile"),
    path("child/add/", views.child_add, name="child_add"),
    path("child/<int:pk>/edit/", views.child_edit, name="child_edit"),
    path("child/<int:pk>/switch/", views.child_switch, name="child_switch"),
]
