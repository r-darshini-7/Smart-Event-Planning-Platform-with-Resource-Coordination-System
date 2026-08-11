import os
import django
from django.contrib.auth import get_user_model
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'event_management.settings')
django.setup()

User = get_user_model()
user, created = User.objects.get_or_create(username='debuguser', defaults={'email': 'debug@example.com'})
if created:
    user.set_password('DebugPass123')
    user.is_staff = True
    user.save()
    print('Created debug user', user.username)
else:
    print('Using debug user', user.username)

client = Client()
client.force_login(user)
print('Force login OK')

paths = ['/', '/create-event/', '/event-list/']
for path in paths:
    print('\nPATH', path)
    try:
        resp = client.get(path)
        print('status', resp.status_code)
        if resp.status_code >= 400:
            print('content:', resp.content.decode('utf-8', errors='replace')[:2000])
        else:
            print('content snippet:', resp.content.decode('utf-8', errors='replace')[:800])
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('EXC', type(e).__name__, e)
