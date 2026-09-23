import re

from django.core.exceptions import ValidationError

TAJIKISTAN_CODE = "992"


def normalize_phone(raw):
    """Приводит номер к виду +<цифры>. Номер из 9 цифр считается таджикским (+992)."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:
        digits = TAJIKISTAN_CODE + digits
    if not 10 <= len(digits) <= 15:
        raise ValidationError("Введите номер телефона, например +992 93 123 45 67.")
    return "+" + digits
