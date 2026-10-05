from django.contrib import admin
from django.utils import timezone

from .models import ConsultationRequest


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    # Класс остаётся в списке ради старых заявок, где он заполнен; в новых его просто нет.
    list_display = ("name", "phone", "grade", "created_at", "handled_at")
    list_filter = ("handled_at",)
    search_fields = ("name", "phone")
    readonly_fields = ("created_at",)
    actions = ["mark_handled"]

    @admin.action(description="Отметить как обработанные")
    def mark_handled(self, request, queryset):
        updated = queryset.filter(handled_at__isnull=True).update(handled_at=timezone.now())
        self.message_user(request, f"Отмечено заявок: {updated}")
