from django.conf import settings
from django.contrib import admin
from django.urls import include, path

# Подписи админки. Без этого Django пишет «Администрирование Django» в шапке, на странице входа
# и в заголовке вкладки — владельцу платформы это слово ни о чём не говорит.
admin.site.site_header = f"{settings.SITE_NAME} — панель управления"
admin.site.site_title = settings.SITE_NAME
admin.site.index_title = "Разделы"

urlpatterns = [
    # Панель управления: курсы, темы, материалы и задания можно добавлять руками.
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("children.urls")),
    path("", include("learning.urls")),
    path("", include("leads.urls")),
]
