from django.apps import AppConfig


class SecmomoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'secmomo'
    
    def ready(self):
        import secmomo.signals  # A line to import the signals.py
