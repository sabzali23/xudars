from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("course/<slug:slug>/", views.course, name="course"),
    path("progress/", views.progress_overview, name="progress"),
    path("topic/<slug:slug>/", views.topic_router, name="topic"),
    re_path(r"^topic/(?P<slug>[-a-zA-Z0-9_]+)/test/(?P<kind>entry|final)/$", views.take_test, name="topic_test"),
    path("topic/<slug:slug>/material/", views.material, name="topic_material"),
    path("topic/<slug:slug>/result/<int:attempt_id>/", views.result, name="topic_result"),
    path("topic/<slug:slug>/next/", views.next_step, name="topic_next"),
    path("topic/<slug:slug>/repeat/", views.repeat, name="topic_repeat"),
]
