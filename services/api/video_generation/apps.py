from django.apps import AppConfig


class VideoGenerationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "video_generation"

    def ready(self):
        from . import checks  # noqa: F401
