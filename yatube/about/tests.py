from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class AboutTests(TestCase):
    """
    Тестирование /about/
    """

    def test_about_author(self):
        """Страница '/about/author/' доступна любому пользователю."""
        response = self.client.get('/about/author/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_about_tech(self):
        """Страница '/about/tech/' доступна любому пользователю."""
        response = self.client.get('/about/tech/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_about_right_template_used(self):
        """Проверяем, что используется правильный шаблон."""
        response = self.client.get('/about/author/')
        self.assertTemplateUsed(response, 'about/author.html')

    def test_author_right_template_used(self):
        """Проверяем, что используется правильный шаблон."""
        response = self.client.get('/about/tech/')
        self.assertTemplateUsed(response, 'about/tech.html')
