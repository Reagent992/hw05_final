import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from posts.models import Post, Group

User = get_user_model()

# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


# Для сохранения media-файлов в тестах будет использоваться
# временная папка TEMP_MEDIA_ROOT, а потом мы ее удалим
@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    def setUp(self):
        """Создаем данные для тестирования"""
        super().setUp()
        # Создаем неавторизованного пользователя
        self.guest_user = Client()

        # Создаем авторизованного пользователя
        self.user = User.objects.create_user(username='test_user')
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)

        # Создаем группу.
        self.group1 = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        # Подготавливаем данные для передачи в форму
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

        # Создаем вторую группу.
        self.group2 = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )

        # Создаем пост.
        self.post1 = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=self.group1,
        )

    def tearDown(self) -> None:
        """Удаляем временную папку для медиа-файлов"""
        super().tearDown()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_post_create_form(self):
        """Форма создает пост."""
        # Подсчитаем количество постов в базе данных
        post_count = Post.objects.count()

        form_data = {
            'text': 'Текст для проверки формы создания поста',
            'group': self.group1.id,
            'image': self.uploaded,
        }
        response = self.authorized_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user.username}
        ))
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), post_count + 1)
        # Проверяем, что создалась запись с нашими данными
        self.assertTrue(
            Post.objects.filter(
                text='Текст для проверки формы создания поста',
                group=self.group1.id,
                image='posts/small.gif'
            ).exists()
        )

    def test_post_edit_form(self):
        """Форма редактирует пост."""
        # Подсчитаем количество постов в базе данных
        post_count = Post.objects.count()

        form_data = {
            'text': 'Отредактированный текст',
            'group': self.group2.id,
            'image': self.uploaded,
        }
        response = self.authorized_user.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post1.id}),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post1.id}
        ))
        # Проверяем, не изменилось ли число постов
        self.assertEqual(Post.objects.count(), post_count)
        # Проверяем, что создалась запись с нашими данными
        self.assertTrue(
            Post.objects.filter(
                text='Отредактированный текст',
                group=self.group2.id,
                image='posts/small.gif'
            ).exists()
        )

    def test_edit_form_fields_are_prepopulated_with_post_data(self):
        """
        Проверяем что форма заполнена данными редактируемого поста.
        """
        response = self.authorized_user.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post1.id}))
        self.assertEqual(
            response.context['form'].initial['text'], self.post1.text
        )
        self.assertEqual(
            response.context['form'].initial['group'], self.post1.group.id
        )
        self.assertEqual(
            response.context['form'].initial['image'], self.post1.image.name
        )
