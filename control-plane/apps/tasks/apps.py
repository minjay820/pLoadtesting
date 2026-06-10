from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "apps.tasks"
    label = "tasks"
    verbose_name = "Tasks"
