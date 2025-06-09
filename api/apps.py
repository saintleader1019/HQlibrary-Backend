from django.apps import AppConfig

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'


    # Solo se ejecuta una vez al iniciar el servidor
    # def ready(self):
    #      from .startup import create_default_root
    #      create_default_root()
