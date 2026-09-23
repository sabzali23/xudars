from django.conf import settings


def site(request):
    return {"SITE_NAME": settings.SITE_NAME, "SITE_CONTACT": settings.SITE_CONTACT}
