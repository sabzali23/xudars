from django.conf import settings
from django.db import models


class Child(models.Model):
    """Профиль ребёнка. В v1 у родителя ровно один ребёнок; храним только необходимый минимум данных."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="children")
    name = models.CharField("Имя ребёнка", max_length=100)
    grade = models.PositiveSmallIntegerField("Класс", choices=[(i, f"{i} класс") for i in range(1, 12)])
    target_school = models.CharField("Целевая школа", max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ребёнок"
        verbose_name_plural = "дети"
        ordering = ["created_at", "pk"]

    def __str__(self):
        return self.name
