from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'applications'

    def ready(self):
        # Importing signals here (rather than at module load time) is the
        # documented Django pattern: it guarantees the app registry is
        # fully populated before signal receivers are connected, and
        # avoids import-order issues between apps.
        import applications.signals  # noqa: F401
