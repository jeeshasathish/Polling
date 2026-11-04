from django.apps import AppConfig


class PollsConfig(AppConfig):
    name = "polls"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import polls.signals  # noqa: F401 — registers post_save signal handlers
