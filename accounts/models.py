from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from .phone import normalize_phone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra_fields):
        user = self.model(phone=normalize_phone(phone), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Родитель. Входит по номеру телефона и паролю."""

    phone = models.CharField(
        "Телефон",
        max_length=20,
        unique=True,
        error_messages={"unique": "Этот номер уже зарегистрирован. Попробуйте войти."},
    )
    name = models.CharField("Ваше имя", max_length=100)
    telegram = models.CharField("Telegram (необязательно)", max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        verbose_name = "родитель"
        verbose_name_plural = "родители"

    def __str__(self):
        return f"{self.name} ({self.phone})"


class PasswordResetRequest(models.Model):
    """Заявка «забыл пароль».

    Ни почты, ни SMS у проекта нет, поэтому пароль восстанавливается через человека: родитель
    оставляет заявку, владелец платформы звонит по указанному номеру и убеждается, что это
    действительно он, и выдаёт одноразовую ссылку на смену пароля. Сама ссылка нигде не хранится:
    она собирается в момент выдачи из стандартного токена Django и перестаёт работать, как только
    пароль изменён или истёк срок (`settings.PASSWORD_RESET_TIMEOUT`).
    """

    phone = models.CharField("Телефон", max_length=20)
    user = models.ForeignKey(
        "accounts.User",
        verbose_name="родитель",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="password_reset_requests",
    )
    created_at = models.DateTimeField("Оставлена", auto_now_add=True)
    handled_at = models.DateTimeField("Ссылка выдана", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "заявка на смену пароля"
        verbose_name_plural = "заявки на смену пароля"

    def __str__(self):
        return f"{self.phone} от {self.created_at:%d.%m.%Y}"
