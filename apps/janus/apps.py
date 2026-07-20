from django.apps import AppConfig

class JanusConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.janus"
    verbose_name = "Janus (Idea Validator)"

    def ready(self):
        from . import signals  # noqa: F401