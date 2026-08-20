from django.db.models import Q
from django.utils import translation

from .models import Notification
from .translations import TRANSLATIONS, translate_text


def preferred_language(request):
    language = request.session.get('preferred_language') or request.session.get('django_language') or translation.get_language() or 'en'
    request.session['preferred_language'] = language
    request.session['django_language'] = language
    translation.activate(language)
    request.LANGUAGE_CODE = language

    def translate(text):
        return translate_text(text, language)

    nav_labels = {
        'admin_panel': translate('Eventon'),
        'main_navigation': translate('MAIN NAVIGATION'),
        'event_category_header': translate('EVENT CATEGORY'),
        'events_header': translate('EVENTS'),
        'members_header': translate('MEMBERS'),
        'wishlist_header': translate('WISHLIST'),
        'attendance_marks_header': translate('ATTENDANCE & MARKS'),
        'dashboard': translate('Dashboard'),
        'event_category': translate('Event Category'),
        'create_category': translate('Create Category'),
        'category_list': translate('Category List'),
        'events': translate('Events'),
        'create_event': translate('Create Event'),
        'event_list': translate('Event List'),
        'add_event_member': translate('Add Event Member'),
        'join_event_list': translate('Join Event List'),
        'event_wish_list': translate('Event Wish List'),
        'add_event_wish_user': translate('Add Event Wish User'),
        'absence_user_list': translate('Absence User List'),
        'complete_event_list': translate('Complete Event List'),
        'create_user_mark': translate('Create User Mark'),
        'user_mark_list': translate('User Mark List'),
        'platform': translate('Event Registration Platform'),
        'messages': translate('Messages'),
        'notifications': translate('Notifications'),
        'customize_adminlte': translate('Customize AdminLTE'),
        'profile': translate('Profile'),
        'setting': translate('Setting'),
        'logout': translate('Logout'),
        'home': translate('Home'),
        'live': translate('Live'),
    }

    page_labels = {
        'dashboard_overview': translate('Event Management Overview'),
        'dashboard_breadcrumb': translate('Dashboard'),
        'categories': translate('Categories'),
        'total_events': translate('Total Events'),
        'registrations': translate('Registrations'),
        'completed': translate('Completed'),
        'event_list': translate('Event List'),
        'create_new_event': translate('Create New Event'),
        'category_list': translate('Category List'),
        'add_category': translate('Add Category'),
        'no_events_yet': translate('No Events Created Yet'),
        'no_categories_found': translate('No Categories Found'),
    }

    user_messages = []
    user_notifications = []
    if request.user.is_authenticated:
        scope_filter = Q(target_scope='both')
        if request.user.is_staff:
            scope_filter |= Q(target_scope='admin')
        else:
            scope_filter |= Q(target_scope='user')
        visible_items = Notification.objects.filter(is_active=True).filter(scope_filter).order_by('-created_at')
        user_messages = list(visible_items.filter(kind='message')[:10])
        user_notifications = list(visible_items.filter(kind='notification')[:10])

    return {
        'preferred_language': language,
        'nav_labels': nav_labels,
        'page_labels': page_labels,
        'translations': {key: translate(key) for key in TRANSLATIONS.keys()},
        'user_messages': user_messages,
        'user_messages_count': len(user_messages),
        'user_notifications': user_notifications,
        'user_notifications_count': len(user_notifications),
    }
