# apps/code_analyzer/apps.py
from django.apps import AppConfig


class CodeAnalyzerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.code_analyzer"
    verbose_name = "Code Analyzer"
