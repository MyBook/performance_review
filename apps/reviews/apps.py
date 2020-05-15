from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    name = 'apps.reviews'

    def ready(self):
        from apps.reviews import receivers  # noqa

