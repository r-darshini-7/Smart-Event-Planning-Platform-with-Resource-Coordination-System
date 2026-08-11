import os
import django
from django.test import Client
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'event_management.settings')
django.setup()

User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    u = User.objects.create_superuser('debugadmin', 'debug@example.com', 'DebugPass123')
    print('Created superuser:', u.username)
else:
    u = User.objects.filter(is_superuser=True).first()
    print('Using superuser:', u.username)

client = Client()
logged = client.login(username=u.username, password='DebugPass123')
print('login ok', logged)
for path in ['/', '/create-event/', '/event-list/', '/event-detail/1/', '/edit-event/1/']:
    print('\nPATH', path)
    try:
        resp = client.get(path)
        print('status', resp.status_code)
        print(resp.content.decode('utf-8', errors='replace')[:1000])
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('EXC', type(e).__name__, e)
