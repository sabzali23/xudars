from django.contrib import admin

from .models import Child


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "grade", "target_school", "created_at")
    list_filter = ("grade",)
    search_fields = ("name", "target_school", "user__phone", "user__name")
    readonly_fields = ("created_at",)
