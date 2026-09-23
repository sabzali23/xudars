from django.db import models


class ConsultationRequest(models.Model):
    """Заявка на бесплатную консультацию с лендинга.

    Храним минимум: как связаться и в каком классе ребёнок. Заявка — это ещё не аккаунт:
    профиль ребёнка появляется только после регистрации родителя.
    """

    name = models.CharField("Имя", max_length=100)
    grade = models.PositiveSmallIntegerField("Класс", choices=[(i, f"{i} класс") for i in range(1, 12)])
    phone = models.CharField("Телефон", max_length=20)
    created_at = models.DateTimeField("Оставлена", auto_now_add=True)
    handled_at = models.DateTimeField("Обработана", null=True, blank=True)

    class Meta:
        verbose_name = "заявка на консультацию"
        verbose_name_plural = "заявки на консультацию"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} · {self.phone}"
