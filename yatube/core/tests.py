from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

User = get_user_model()


class CoreTest(TestCase):
    def test_core_404(self):
        """
        Страница 404 отдает ожидаемый шаблон.
        """
        if not settings.DEBUG:
            url_templates_dict = {
                '/nonexistent/': 'core/404.html',

            }
            for url, template in url_templates_dict.items():
                with self.subTest(url=url, template=template):
                    cache.clear()
                    response = self.client.get(url)
                    self.assertTemplateUsed(response, template)
