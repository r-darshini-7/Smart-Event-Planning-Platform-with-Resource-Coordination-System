from django import template

register = template.Library()

LABELS = {
    'dashboard': {
        'en': 'Dashboard',
        'kn': 'ಡ್ಯಾಶ್ಬೋರ್ಡ್',
    },
    'event_category': {
        'en': 'Event Category',
        'kn': 'ಈವೆಂಟ್ ವರ್ಗ',
    },
    'create_category': {
        'en': 'Create Category',
        'kn': 'ವರ್ಗ ರಚಿಸಿ',
    },
    'category_list': {
        'en': 'Category List',
        'kn': 'ವರ್ಗಗಳ ಪಟ್ಟಿ',
    },
    'events': {
        'en': 'Events',
        'kn': 'ಈವೆಂಟ್ಸ್',
    },
    'add_event_member': {
        'en': 'Add Event Member',
        'kn': 'ಈವೆಂಟ್ ಸದಸ್ಯರನ್ನ ಸೇರಿಸಿ',
    },
    'join_event_list': {
        'en': 'Join Event List',
        'kn': 'ಈವೆಂಟ್ ಸೇರಲು ಪಟ್ಟಿ',
    },
    'event_wish_list': {
        'en': 'Event Wish List',
        'kn': 'ಈವೆಂಟ್ ಇಚ್ಛೆಗಳ ಪಟ್ಟಿ',
    },
    'add_event_wish_user': {
        'en': 'Add Event Wish User',
        'kn': 'ಇಚ್ಛೆ ಬಳಕೆದಾರರನ್ನು ಸೇರಿಸಿ',
    },
    'absence_user_list': {
        'en': 'Absence User List',
        'kn': 'ಅನುಪಸ್ಥಿತಿಯ ಬಳಕೆದಾರರ ಪಟ್ಟಿ',
    },
    'complete_event_list': {
        'en': 'Complete Event List',
        'kn': 'ಸಂಪೂರ್ಣಈವೆಂಟ್ ಪಟ್ಟಿ',
    },
    'create_user_mark': {
        'en': 'Create User Mark',
        'kn': 'ಬಳಕೆದಾರ ಗುರುತು ರಚಿಸಿ',
    },
    'user_mark_list': {
        'en': 'User Mark List',
        'kn': 'ಬಳಕೆದಾರ ಗುರುತು ಪಟ್ಟಿ',
    },
}

@register.simple_tag(takes_context=True)
def lang_label(context, key):
    language = context.get('preferred_language', 'en')
    if language in ('kn', 'kn-in'):
        language = 'en'
    return LABELS.get(key, {}).get(language, LABELS.get(key, {}).get('en', key))
