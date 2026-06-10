from django.apps import AppConfig


class WorkersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "apps.workers"
    label = "workers"
    verbose_name = "Workers"
