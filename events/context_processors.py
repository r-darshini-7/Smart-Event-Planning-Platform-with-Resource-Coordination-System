from django.db.models import Q
from django.utils import translation

from .models import Notification
from .translations import TRANSLATIONS, translate_text


def preferred_language(request):
    language = 'en'
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
        'analytics': translate('Analytics'),
        'search_events': translate('Search events...'),
        'calendar': translate('Calendar'),
        'scan_qr_code': translate('Scan QR Code'),
        'loading_cameras': translate('Loading cameras...'),
        'camera_unavailable': translate('Camera unavailable.'),
        'cancel': translate('Cancel'),
        'torch': translate('Torch'),
        'scan_qr': translate('Scan QR'),
        'venue_management': translate('VENUE MANAGEMENT'),
        'venues': translate('Venues'),
        'add_venue': translate('Add Venue'),
        'venue_list': translate('Venue List'),
        'venue_bookings': translate('Venue Bookings'),
        'book_venue': translate('Book Venue'),
        'bookings_list': translate('Bookings List'),
        'resource_management': translate('RESOURCE MANAGEMENT'),
        'resources': translate('Resources'),
        'add_resource': translate('Add Resource'),
        'resource_list': translate('Resource List'),
        'allocations': translate('Allocations'),
        'allocate_resource': translate('Allocate Resource'),
        'allocation_list': translate('Allocation List'),
        'vendor_management': translate('VENDOR MANAGEMENT'),
        'vendors': translate('Vendors'),
        'add_vendor': translate('Add Vendor'),
        'vendor_list': translate('Vendor List'),
        'assignments': translate('Assignments'),
        'assign_vendor': translate('Assign Vendor'),
        'assignment_list': translate('Assignment List'),
        'sponsors': translate('Sponsors'),
        'add_sponsor': translate('Add Sponsor'),
        'sponsor_list': translate('Sponsor List'),
        'budget_finance': translate('BUDGET & FINANCE'),
        'budget': translate('Budget'),
        'add_budget_item': translate('Add Budget Item'),
        'budget_item_list': translate('Budget Item List'),
        'workflow': translate('WORKFLOW'),
        'approvals': translate('Approvals'),
        'new_request': translate('New Request'),
        'approvals_list': translate('Approvals List'),
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
        recipient_filter = Q(recipient=request.user) | Q(recipient__isnull=True)
        visible_items = Notification.objects.filter(is_active=True).filter(scope_filter).filter(recipient_filter).order_by('-created_at')
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
