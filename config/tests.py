"""Проверки настроек, от которых зависит работа сайта на своём домене.

Ошибка здесь не ломает тесты приложения, зато ломает боевой сайт: при неверном списке
Django отвечает 400 на каждую страницу, а формы входа и заявки — 403 из-за проверки CSRF.
"""

import importlib
import os
from unittest import mock

from django.test import SimpleTestCase


class HostSettingsTests(SimpleTestCase):
    def load(self, **env):
        """Перечитывает config/settings.py с заданными переменными окружения."""
        import config.settings as module

        # После проверки возвращаем модуль в исходное состояние, чтобы не влиять на другие тесты.
        self.addCleanup(importlib.reload, module)
        with mock.patch.dict(os.environ, env, clear=False):
            return importlib.reload(module)

    def test_custom_domain_gets_a_trusted_origin(self):
        settings = self.load(
            DJANGO_ALLOWED_HOSTS="xudars.tj,www.xudars.tj", RENDER_EXTERNAL_HOSTNAME="xudars.onrender.com"
        )
        self.assertIn("xudars.tj", settings.ALLOWED_HOSTS)
        self.assertIn("https://xudars.tj", settings.CSRF_TRUSTED_ORIGINS)
        self.assertIn("https://www.xudars.tj", settings.CSRF_TRUSTED_ORIGINS)

    def test_old_render_address_keeps_working_next_to_the_domain(self):
        settings = self.load(
            DJANGO_ALLOWED_HOSTS="xudars.tj", RENDER_EXTERNAL_HOSTNAME="xudars.onrender.com"
        )
        self.assertIn("xudars.onrender.com", settings.ALLOWED_HOSTS)
        self.assertIn("https://xudars.onrender.com", settings.CSRF_TRUSTED_ORIGINS)

    def test_render_address_is_not_duplicated(self):
        settings = self.load(
            DJANGO_ALLOWED_HOSTS="xudars.onrender.com", RENDER_EXTERNAL_HOSTNAME="xudars.onrender.com"
        )
        self.assertEqual(settings.ALLOWED_HOSTS.count("xudars.onrender.com"), 1)
        self.assertEqual(settings.CSRF_TRUSTED_ORIGINS.count("https://xudars.onrender.com"), 1)

    def test_local_addresses_do_not_become_https_origins(self):
        """localhost ходит по http, и в списке доверенных источников ему делать нечего."""
        settings = self.load(DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1")
        self.assertEqual(settings.CSRF_TRUSTED_ORIGINS, [])

    def test_spaces_around_names_are_trimmed(self):
        """В панели хостинга список почти всегда вписывают с пробелами после запятой."""
        settings = self.load(DJANGO_ALLOWED_HOSTS="xudars.tj, www.xudars.tj")
        self.assertIn("www.xudars.tj", settings.ALLOWED_HOSTS)
        self.assertIn("https://www.xudars.tj", settings.CSRF_TRUSTED_ORIGINS)
