# apps/atlas/apps.py
from django.apps import AppConfig


class AtlasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.atlas"
    label = "atlas"
    verbose_name = "Atlas"
