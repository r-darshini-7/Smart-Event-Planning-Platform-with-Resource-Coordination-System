import os
import django
import pathlib

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'event_management.settings')
django.setup()
from events.forms import EventForm, EventCreateForm
from events.models import Event
from django.conf import settings

print('cwd=', pathlib.Path.cwd())
print('db_name=', settings.DATABASES['default']['NAME'])
print('Event model fields=', [f.name for f in Event._meta.fields])
print('EventForm.Meta.fields=', EventForm.Meta.fields)
print('EventCreateForm.Meta.fields=', EventCreateForm.Meta.fields)
