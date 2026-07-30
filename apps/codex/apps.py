from django.apps import AppConfig


class CodexConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.codex"
    label = "codex"
    verbose_name = "Codex — Markdown Library"
