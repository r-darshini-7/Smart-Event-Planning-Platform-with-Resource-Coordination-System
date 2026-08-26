from bson import ObjectId
from django.apps import AppConfig
from django.apps import apps as global_apps
from django.contrib.admin.apps import AdminConfig
from django.contrib.auth.apps import AuthConfig
from django.contrib.auth.management import create_permissions
from django.contrib.contenttypes.apps import ContentTypesConfig
from django.db.models.signals import post_migrate
from django_mongodb_backend.fields import ObjectIdAutoField


class MongoObjectIdAutoField(ObjectIdAutoField):
    def get_pk_value_on_save(self, instance):
        if instance.pk is None:
            return ObjectId()
        return instance.pk


MONGO_AUTO_FIELD = 'mongo_apps.MongoObjectIdAutoField'


class MongoAdminConfig(AdminConfig):
    default_auto_field = MONGO_AUTO_FIELD


class MongoAuthConfig(AuthConfig):
    default_auto_field = MONGO_AUTO_FIELD

    def ready(self):
        super().ready()
        post_migrate.disconnect(
            dispatch_uid='django.contrib.auth.management.create_permissions'
        )
        post_migrate.connect(
            _create_mongo_permissions,
            dispatch_uid='mongo_apps.create_permissions',
        )


class MongoContentTypesConfig(ContentTypesConfig):
    default_auto_field = MONGO_AUTO_FIELD


def _create_mongo_permissions(sender, **kwargs):
    kwargs['apps'] = global_apps
    app_config = kwargs.pop('app_config', sender)
    create_permissions(app_config, **kwargs)
