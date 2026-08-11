import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'event_management.settings')
import django
from django.contrib.auth import get_user_model
from django.test import Client

django.setup()
from events.models import Category

User = get_user_model()
user, created = User.objects.get_or_create(username='debuguser', defaults={'email': 'debug@example.com'})
if created:
    user.set_password('DebugPass123')
    user.is_staff = True
    user.save()
    print('Created debug user', user.username)
else:
    print('Using debug user', user.username)

category, _ = Category.objects.get_or_create(name='DebugCategory', defaults={'code': 'debug-category', 'priority': 1, 'status': 'active'})
print('Using category', category.id, category.name)

client = Client()
client.force_login(user)

resp = client.post('/create-event/', {
    'uid': 'DEBUG001',
    'title': 'Debug Event',
    'description': 'Debug event description',
    'image': '',
    'session_name': 'Debug Session',
    'speaker_name': 'Debug Speaker',
    'start_time': '2026-07-30T10:00',
    'end_time': '2026-07-30T12:00',
    'venue_name': 'Debug Venue',
    'location': 'Debug Location',
    'map_latitude': '12.971598',
    'map_longitude': '77.594566',
    'price': '0.00',
    'points': '10',
    'max_attendance': '10',
    'job_category': 'other',
    'status': 'live',
    'category_type': 'Tech Fest',
}, follow=True)
print('POST status', resp.status_code)
print('redirect chain', resp.redirect_chain)
print('content snippet', resp.content.decode('utf-8', errors='replace')[:1200])
