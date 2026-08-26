from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = 'mongo_apps.MongoObjectIdAutoField'
    name = 'events'
