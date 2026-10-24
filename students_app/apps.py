from django.apps import AppConfig


class StudentsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'students_app'

    def ready(self):
        from . import image_optimizer
        image_optimizer.connect()