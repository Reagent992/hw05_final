import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from posts.models import Post, Group, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ViewsTests(TestCase):
    """
    1. Шаблоны.
    2. Контекст.
    3. Работа групп.
    4. Комментарии
    5. Кэш
    6. Подписки
    7. Паджинатор.
    """

    def setUp(self):
        """Создаем данные для тестов."""
        super().setUp()
        # Создаем неавторизованного пользователя.
        self.guest_user = Client()

        # Создаем первого авторизованного пользователя.
        self.user1 = User.objects.create_user(username='test_user')
        self.authorized_user1 = Client()
        self.authorized_user1.force_login(self.user1)

        # Создаем второго авторизованного пользователя.
        self.user2 = User.objects.create_user(username='test_user2')
        self.authorized_user2 = Client()
        self.authorized_user2.force_login(self.user2)

        # Создаем третьего авторизованного пользователя.
        self.user3 = User.objects.create_user(username='test_user3')
        self.authorized_user3 = Client()
        self.authorized_user3.force_login(self.user3)

        # Создаем группу.
        self.group1 = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        # Создаем вторую группу.
        self.group2 = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )
        # Создаем картинку.
        self.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        self.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        # Отправляем пост "через форму".
        self.authorized_user1.post(
            reverse('posts:post_create'),
            data={
                'text': 'Тестовый текст',
                'group': self.group1.id,
                'image': self.uploaded,
            }
        )
        # Присваиваем его переменной.
        self.post1 = Post.objects.get(text='Тестовый текст')
        # Временный пост для проверки кэша главной страницы.
        Post.objects.create(
            text='31fgr2g21rgf43fvb',
            author=self.user1,
            group=self.group1,
        )

        # Данные для комментариев.
        self.data = {'text': 'test_comment1526'}
        # Отправка комментария от авторизованного пользователя.
        self.authorized_user1.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post1.id}),
            self.data)
        # Присваиваем созданный комментарий переменной.
        self.comment = self.post1.comments.get(text=self.data['text'])

    def tearDown(self) -> None:
        """Удаляем временную папку для медиа-файлов"""
        super().tearDown()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_uses_correct_template(self):
        """
        1. view-классы используют ожидаемые HTML-шаблоны.
        """
        # Собираем в словарь пары "reverse(name)":имя_html_шаблона
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:follow_index'): 'posts/follow.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group1.slug}
                    ): 'posts/group_list.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group1.slug}
                    ): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.user1.username}
                    ): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post1.id}
                    ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post1.id}
                    ): 'posts/create_post.html',
        }
        # Проверяем, что при обращении к name
        # вызывается соответствующий HTML-шаблон
        for reverse_name, template in templates_page_names.items():
            with self.subTest(reverse_name=reverse_name, template=template):
                cache.clear()
                response = self.authorized_user1.get(reverse_name)
                self.assertTemplateUsed(response, template)

        """
        2. В шаблон передан правильный контекст
        """

    def test_post_context_in_index_group_profile_post_detail(self):
        """2.1 Context содержит тестовый пост"""
        # Собираем в словарь пары "response(name)":имя_объекта_context
        reverse_name = {
            reverse('posts:index'): 'page_obj',
            reverse('posts:group_list',
                    kwargs={'slug': self.group1.slug}): 'page_obj',
            reverse('posts:profile',
                    kwargs={'username': self.user1.username}): 'page_obj',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post1.id}): 'post',
        }
        # Проверяем, что в context есть все из тестового поста.
        for reverse_name, obj_name in reverse_name.items():
            with self.subTest(reverse_name=reverse_name, obj_name=obj_name):
                response = self.guest_user.get(reverse_name)
                # В post_detail 1 объект, тестируем отдельно.
                if obj_name == 'post':
                    post_test = response.context[obj_name]
                else:
                    post_test = response.context[obj_name][self.post1.id]
                self.assertEqual(post_test.text, self.post1.text)
                self.assertEqual(post_test.author, self.post1.author)
                self.assertEqual(post_test.group, self.post1.group)
                self.assertEqual(post_test.image, self.post1.image)

    def test_post_create_and_edit_page_show_correct_context(self):
        """
        2.2 Проверяем формы создаваемые view-функциями
        post_create и post_create_edit.
        """
        # Адреса проверяемых страниц
        urls = [reverse('posts:post_create'),
                reverse('posts:post_edit', kwargs={'post_id': self.post1.id})]
        # Словарь ожидаемых типов полей формы:
        # указываем, объектами какого класса должны быть поля формы
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField,
        }
        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_user1.get(url)
                # Проверяем, что типы полей формы в словаре context
                # соответствуют ожиданиям
                for field_name, expected_field_type in form_fields.items():
                    with self.subTest(field_name=field_name):
                        form_field = response.context.get('form').fields.get(
                            field_name)
                        self.assertIsInstance(form_field, expected_field_type)

    '''
    3. Работа групп.
    '''

    def test_post_exist_on_index(self):
        """Созданный пост появляется на главной странице сайта."""
        response = self.authorized_user1.get(reverse('posts:index'))
        self.assertContains(response, self.post1, status_code=200)

    def test_post_exist_on_author_page(self):
        """Созданный пост появляется на странице автора поста."""
        response = self.authorized_user1.get(reverse(
            'posts:profile',
            kwargs={'username': self.user1.username}))
        self.assertContains(response, self.post1, status_code=200)

    def test_post_going_to_right_group(self):
        """post1 из группы group1 появился в group1."""
        response = self.guest_user.get(
            reverse('posts:group_list', kwargs={'slug': self.group1.slug}
                    ))
        self.assertContains(response, self.post1, status_code=200)

    def test_post_not_going_to_wrong_group(self):
        """post1 из группы group1 не должен попасть в group2."""
        # Открываем вторую группу.
        response = self.guest_user.get(
            reverse('posts:group_list', kwargs={'slug': self.group2.slug}
                    ))
        # Проверяем отсутствие поста.
        self.assertNotContains(response, self.post1, status_code=200)

    """
    4. Проверка Комментариев.
    """

    def test_comments_allowed_to_auth_user_only(self):
        """4.1 Комментировать может только авторизованный."""
        self.comment_data = {'text': 'test_comment345436'}
        # отправка комментария от неавторизованного пользователя
        self.guest_user.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post1.id}),
            self.comment_data)

        # "открываем" страницу поста
        response = self.guest_user.get(
            reverse('posts:post_detail', args=[self.post1.id]))
        # проверяем что комментарий не появился на странице
        self.assertNotContains(
            response,
            self.comment_data['text'],
            status_code=200
        )

    def test_comment_post_and_check(self):
        """
        4.2 После успешной отправки комментарий появляется на странице поста.
        """
        # Комментарий для post1 отправлен в setUp().
        # Проверка появления комментария на странице поста.
        response = self.guest_user.get(
            reverse('posts:post_detail', args=[self.post1.id]))
        print(response.request)

        self.assertContains(response, self.comment, status_code=200)

    def test_cache_index(self):
        """
        5. Проверка кэша главной страницы.
        """
        # Проверяем наличие временного поста(из фикстур) на главной странице.
        response = self.authorized_user1.get(reverse('posts:index'))
        self.assertContains(response, '31fgr2g21rgf43fvb', status_code=200)
        # Удаляем пост.
        Post.objects.filter(text='31fgr2g21rgf43fvb').delete()
        # Проверяем что он остался в кэше главной страницы.
        response2 = self.authorized_user1.get(reverse('posts:index'))
        self.assertContains(response2, '31fgr2g21rgf43fvb', status_code=200)
        # Чистим кэш.
        cache.clear()
        # Проверяем что пост пропал с главной страницы.
        response3 = self.authorized_user1.get(reverse('posts:index'))
        self.assertNotContains(response3, '31fgr2g21rgf43fvb', status_code=200)

    """
    6. Проверка подписок.
    """

    def test_user_can_subscribe_and_unsubscribe(self):
        """6.1 Пользователь может подписываться и отписываться."""
        # Подписываемся.
        response = self.authorized_user1.get(
            reverse(
                'posts:profile_follow',
                args=[self.user2.username]
            ))
        # Проверка редиректа.
        self.assertEqual(response.status_code, 302)
        # Выбираем запись подписки в БД.
        follow = Follow.objects.filter(
            user=self.user1,
            author=self.user2
        )
        # Проверяем, что подписка создана.
        self.assertTrue(follow.exists())

        # Отписываемся.
        response = self.authorized_user1.get(
            reverse(
                'posts:profile_unfollow',
                args=[self.user2.username]
            ))
        # Проверка редиректа.
        self.assertEqual(response.status_code, 302)
        # Ищем запись подписки в БД.
        follow = Follow.objects.filter(
            user=self.user1,
            author=self.user2
        )
        # Проверяем, что подписка удалена.
        self.assertFalse(follow.exists())

    def test_feeds(self):
        """6.2 Пост появляется в ленте подписчиков."""
        # В фикстурах создан пост от user1;
        # user2 подписывается на user1.
        self.authorized_user2.get(
            reverse(
                'posts:profile_follow',
                args=[self.user1.username]
            ))
        # Проверяем, что пост есть в ленте user2.
        response = self.authorized_user2.get(reverse('posts:follow_index'))
        self.assertEqual(
            response.context['page_obj'][self.post1.id], self.post1
        )
        # Проверяем, что пост отсутствует в ленте не подписанного user3.
        response = self.authorized_user3.get(reverse('posts:follow_index'))
        self.assertNotIn(self.post1, response.context['page_obj'])

    def test_user_cant_subscribe_to_self(self):
        """6.3 Пользователь не может подписываться на себя."""
        # Попытка подписаться на себя.
        self.authorized_user1.get(
            reverse(
                'posts:profile_follow',
                args=[self.user1.username]
            ))
        # Проверяем, что пост отсутствует в ленте.
        response = self.authorized_user1.get(reverse('posts:follow_index'))
        self.assertNotIn(self.post1, response.context['page_obj'])


class PaginatorViewsTest(TestCase):
    """
    7. Проверка паджинатора,
    на страницах должно быть до 10 постов.
    """

    def setUp(self):
        """Создание тестовых данных."""
        # Создаем пользователя
        self.user = User.objects.create_user(username='test_user')

        # Создаем группу
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        # Создаем 13 постов для проверки паджинатора.
        self.post_list = [
            Post(
                text=f'Test post {i}',
                author=self.user,
                group=self.group
            ) for i in range(13)
        ]
        Post.objects.bulk_create(self.post_list)

    def test_pages_paginate(self):
        """Проверка паджинатора на главной, группах и профиле."""
        # Адреса проверяемых страниц.
        urls = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username})
        }
        for url in urls:
            with self.subTest(url=url):
                cache.clear()
                response = self.client.get(url)
                response2 = self.client.get(url + '?page=2')
                # На странице выводится правильное количество постов.
                self.assertEqual(len(response.context['page_obj']), 10)
                self.assertEqual(len(response2.context['page_obj']), 3)
                # Посты на страницах не повторяются.
                self.assertNotContains(response, response2.context['page_obj'])
