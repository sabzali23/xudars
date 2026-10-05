from django.contrib import admin, messages
from django.utils import timezone

from .models import PasswordResetRequest, User
from .reset import reset_link


def _issue_links(request, users_with_rows):
    """Показывает одноразовые ссылки прямо в админке — их копируют родителю в Telegram.

    Ссылку нельзя присылать автоматически: ни почты, ни SMS у проекта нет. Поэтому её выдаёт
    человек и только после того, как убедился по телефону, что просит действительно родитель.
    """
    for user, row in users_with_rows:
        if user is None:
            messages.warning(request, "Заявка без родителя: номер не зарегистрирован или аккаунт удалён.")
            continue
        messages.success(request, f"{user.name} ({user.phone}) — ссылка на сутки: {reset_link(request, user)}")
        if row is not None:
            row.handled_at = timezone.now()
            row.save(update_fields=["handled_at"])


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Родители. Пароль не редактируется здесь: он хранится в виде хеша и меняется через сайт."""

    list_display = ("phone", "name", "telegram", "is_active", "is_staff", "date_joined")
    list_filter = ("is_staff", "is_active")
    search_fields = ("phone", "name", "telegram")
    fields = ("phone", "name", "telegram", "is_active", "is_staff", "is_superuser", "date_joined")
    readonly_fields = ("date_joined",)
    actions = ["issue_password_reset_link"]

    @admin.action(description="Выдать ссылку для смены пароля")
    def issue_password_reset_link(self, request, queryset):
        _issue_links(request, [(user, None) for user in queryset])


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    """Заявки «забыл пароль». Порядок работы: позвонить по номеру → убедиться, что это родитель →
    выдать ссылку действием ниже → отправить её родителю."""

    list_display = ("phone", "parent_name", "telegram", "created_at", "handled_at")
    list_filter = ("handled_at",)
    search_fields = ("phone", "user__name", "user__telegram")
    readonly_fields = ("phone", "user", "created_at", "handled_at")
    actions = ["issue_password_reset_link"]

    @admin.display(description="Родитель")
    def parent_name(self, obj):
        return obj.user.name if obj.user else "—"

    @admin.display(description="Telegram")
    def telegram(self, obj):
        return obj.user.telegram if obj.user and obj.user.telegram else "—"

    @admin.action(description="Выдать ссылку для смены пароля")
    def issue_password_reset_link(self, request, queryset):
        _issue_links(request, [(row.user, row) for row in queryset.select_related("user")])

    def has_add_permission(self, request):
        return False
