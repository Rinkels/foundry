# apps/mnemos/apps.py
from django.apps import AppConfig

class MnemosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mnemos"
    label = "mnemos"  # important for ContentType + app_label consistency
    verbose_name = "Mnemos"
