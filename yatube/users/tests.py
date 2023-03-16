from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

User = get_user_model()

'''
Проверяем только страницы login, signup и logout
т.к. остальные страницы не работают местами.
1. проверяем что страницы открываются для неавторизованного пользователя
2. проверяем соответствие шаблонов и url страниц
3. проверяем на 404
'''


class LoginTest(TestCase):
    def setUp(self):
        """Создаем данные для тестов."""
        super().setUp()
        # Создаем неавторизованного пользователя.
        self.guest_user = Client()

        # Создаем авторизованного пользователя.
        self.user = User.objects.create_user(username='test_user')
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)

    def test_urls_guest(self):
        """Страницы доступные любому пользователю"""
        url_status_dict = {
            'users:login': HTTPStatus.OK,
            'users:signup': HTTPStatus.OK,
            'users:logout': HTTPStatus.OK,
            'users:password_reset_form': HTTPStatus.OK,
            'users:password_reset_done': HTTPStatus.OK,
        }
        for url, status in url_status_dict.items():
            with self.subTest(url=url, status=status):
                response = self.authorized_user.get(reverse(url))
                self.assertEqual(response.status_code, status)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        url_templates_dict = {
            'users:login': 'users/login.html',
            'users:signup': 'users/signup.html',
            'users:logout': 'users/logged_out.html',
            'users:password_reset_form': 'users/password_reset_form.html',
            'users:password_reset_done': 'users/password_reset_done.html',
            'users:password_reset_complete':
                'users/password_reset_complete.html',
        }
        for url, template in url_templates_dict.items():
            with self.subTest(url=url):
                response = self.authorized_user.get(reverse(url))
                print(response.status_code)
                self.assertTemplateUsed(response, template)

    def test_urls_404(self):
        """Возвращается 404 для несуществующих URL"""
        url_status_dict = {
            '/auth/404/': HTTPStatus.NOT_FOUND,
        }
        for url, status in url_status_dict.items():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status)
