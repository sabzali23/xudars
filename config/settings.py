"""Настройки Django-проекта."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-in-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
CSRF_TRUSTED_ORIGINS = []

# Render подставляет адрес приложения сам; без этого сайт после первого развёртывания ответит 400,
# а формы входа и заявки — 403 из-за проверки источника запроса.
RENDER_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOSTNAME}")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "children",
    "curriculum",
    "learning",
    "leads",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "learning.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# На хостинге база задаётся одной переменной DATABASE_URL (PostgreSQL), локально остаётся SQLite.
if os.environ.get("DATABASE_URL"):
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(
        os.environ["DATABASE_URL"], conn_max_age=600, ssl_require=True
    )

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

# Родитель не должен заново входить каждый день.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 90

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Dushanbe"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # За обратным прокси хостинга Django иначе считает соединение незащищённым и зацикливает redirect.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Сайт ---

# Рабочее название проекта ещё не выбрано — заменить перед публикацией.
SITE_NAME = os.environ.get("SITE_NAME", "XuDars")
# Контакт в футере лендинга (Telegram или телефон). Пустая строка — строка контакта не показывается.
SITE_CONTACT = os.environ.get("SITE_CONTACT", "")
# Предметы, показанные в каталоге как «Скоро» (неактивны в v1).
# Подставить те, что реально входят во вступительный экзамен целевой школы.
COMING_SOON_COURSES = []

# Истории учеников в слайдере на лендинге. Сейчас это образцы — заменить на реальные,
# и только с согласия родителей. В «photo» — путь относительно static/; пустое значение
# показывает заглушку. Пока стоят рисованные картинки-образцы (не фото реальных детей):
# заменить на настоящие фото, положив файлы в static/img/students/.
STUDENT_STORIES = [
    {
        "name": "[Имя ученика]",
        "detail": "4 класс · Хорог",
        "topic": "Обыкновенные дроби",
        "before": 40,
        "after": 100,
        "photo": "img/students/sample-1.svg",
    },
    {
        "name": "[Имя ученика]",
        "detail": "3 класс · Хорог",
        "topic": "Проценты",
        "before": 20,
        "after": 80,
        "photo": "img/students/sample-2.svg",
    },
    {
        "name": "[Имя ученика]",
        "detail": "4 класс · Хорог",
        "topic": "Задачи на движение",
        "before": 60,
        "after": 100,
        "photo": "img/students/sample-3.svg",
    },
]

# --- Правила учебного цикла ---

# Итоговый балл (в процентах), начиная с которого тема считается пройденной.
PASS_THRESHOLD = 80
# Количество заданий во входном и итоговом тесте.
TEST_SIZE = 5
# Папка с учебным контентом (разделы, темы, конспекты, задания).
CONTENT_DIR = BASE_DIR / "content"
