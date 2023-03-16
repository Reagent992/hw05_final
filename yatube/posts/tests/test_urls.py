from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse

from posts.models import Post, Group

User = get_user_model()


class PostURLTests(TestCase):
    """
    Тесты для URL-адресов приложения posts.
    """

    def setUp(self):
        """Создаем данные для тестирования"""
        super().setUp()
        # Создаем неавторизованного пользователя
        self.guest_client = Client()

        # Создаем авторизованного пользователя
        self.user = User.objects.create_user(username='test_user')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        # Создаем второго авторизованного пользователя
        self.user2 = User.objects.create_user(username='test_user2')
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user2)

        # Создаем группу.
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        # Создаем пост.
        self.post = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=self.group,
        )

    def test_urls_guest(self):
        """Страницы доступные любому пользователю"""
        url_status_dict = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.user.username}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/': HTTPStatus.OK,
        }
        for url, status in url_status_dict.items():
            with self.subTest(url=url, status=status):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, status)

    def test_urls_authorized(self):
        """Страницы доступные только авторизованным пользователям"""
        url_status_dict = {
            f'/posts/{self.post.id}/edit/': HTTPStatus.OK,
            '/create/': HTTPStatus.OK,
        }
        for url, status in url_status_dict.items():
            with self.subTest(url=url, status=status):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, status)

    def test_urls_404(self):
        """Возвращается 404 для несуществующих URL"""
        url_status_dict = {
            '/404/': HTTPStatus.NOT_FOUND,
            '/group/404/': HTTPStatus.NOT_FOUND,
            '/profile/404/': HTTPStatus.NOT_FOUND,
            '/posts/404/': HTTPStatus.NOT_FOUND,
        }
        for url, status in url_status_dict.items():
            with self.subTest(url=url, status=status):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, status)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        url_templates_dict = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
        }
        for url, template in url_templates_dict.items():
            with self.subTest(url=url, template=template):
                cache.clear()
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_url_redirect_anonymous(self):
        """Требующие авторизации страницы перенаправят анонимного пользователя
        на страницу авторизации."""
        urls_dict = {
            '/create/',
        }
        # получаем адрес авторизации /auth/login/
        login_url = reverse('login')
        for url in urls_dict:
            with self.subTest(url=url):
                # предполагаемый адрес редиректа
                target_url = f'{login_url}?next={url}'
                # реальный адрес редиректа
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(response, target_url)

    def test_another_user_cant_edit_post(self):
        """Пользователь не может изменить чужой пост. Происходит редирект"""
        url_status_dict = {
            f'/posts/{self.post.id}/edit/': HTTPStatus.FOUND,
        }
        for url, status in url_status_dict.items():
            with self.subTest(url=url, status=status):
                response = self.authorized_client2.get(url)
                self.assertEqual(response.status_code, status)
