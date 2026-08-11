from django import template
from django.utils import translation

from events.translations import translate_text

register = template.Library()


@register.filter(is_safe=True)
def tr(value, language=None):
    if not isinstance(value, str):
        return value

    if language is None:
        language = translation.get_language() or 'en'

    return translate_text(value, language)
