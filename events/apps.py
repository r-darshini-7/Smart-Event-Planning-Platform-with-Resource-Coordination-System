from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'events'

    def ready(self):
        # Wire up MongoDB sync signals
        try:
            from .mongo_sync import _connect_signals
            _connect_signals()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "MongoDB signal wiring skipped: %s", exc
            )
