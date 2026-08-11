import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'event_management.settings')
import django
django.setup()
from events import models as evmodels
import inspect

print('module file:', evmodels.__file__)
print('Event fields:', [f.name for f in evmodels.Event._meta.fields])
print('has map_image?', any(f.name == 'map_image' for f in evmodels.Event._meta.fields))
print('model source starts:')
source = inspect.getsource(evmodels.Event)
print('\n'.join(source.splitlines()[:80]))
