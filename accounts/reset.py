"""Одноразовая ссылка на смену пароля.

Ссылка собирается из стандартного токена Django: в него входит хеш текущего пароля, поэтому
после смены пароля старая ссылка перестаёт работать сама. Срок жизни — `PASSWORD_RESET_TIMEOUT`.
"""

from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def reset_path(user):
    """Путь к странице смены пароля для этого родителя."""
    return reverse(
        "password_reset_confirm",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        },
    )


def reset_link(request, user):
    """Полный адрес, который можно отправить родителю в Telegram или продиктовать."""
    return request.build_absolute_uri(reset_path(user))
