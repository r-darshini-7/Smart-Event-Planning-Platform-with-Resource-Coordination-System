from django.utils import translation


class PreferredLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = request.session.get('preferred_language') or request.session.get('django_language') or 'en'
        request.LANGUAGE_CODE = language
        translation.activate(language)
        return self.get_response(request)
