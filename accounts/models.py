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
