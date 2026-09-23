from django.urls import include, path

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("children.urls")),
    path("", include("learning.urls")),
    path("", include("leads.urls")),
]
