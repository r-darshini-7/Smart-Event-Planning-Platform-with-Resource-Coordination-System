from html.parser import HTMLParser
from pathlib import Path
import re
from functools import lru_cache

from django.utils import translation

from .translations import translate_text


class _StaticTextTranslator(HTMLParser):
    def __init__(self, language):
        super().__init__(convert_charrefs=False)
        self.language = language
        self.output = []

    def handle_data(self, data):
        stripped = data.strip()
        if stripped and stripped in _template_static_texts():
            data = data.replace(stripped, translate_text(stripped, self.language), 1)
        self.output.append(data)

    def handle_decl(self, decl):
        self.output.append(f'<!{decl}>')

    def handle_comment(self, data):
        self.output.append(f'<!--{data}-->')

    def handle_entityref(self, name):
        self.output.append(f'&{name};')

    def handle_charref(self, name):
        self.output.append(f'&#{name};')

    def handle_starttag(self, tag, attrs):
        self.output.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.output.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.output.append(f'</{tag}>')

    def handle_pi(self, data):
        self.output.append(f'<?{data}>')

    def result(self):
        return ''.join(self.output)


@lru_cache(maxsize=1)
def _template_static_texts():
    root = Path(__file__).resolve().parent.parent / 'templates'
    phrases = set()
    for path in root.rglob('*.html'):
        source = path.read_text(encoding='utf-8')
        for match in re.finditer(r'>\s*([^<>{}\n]+?)\s*<', source):
            phrase = ' '.join(match.group(1).split())
            if len(phrase) > 1 and not phrase.startswith(('%', '#')):
                phrases.add(phrase)
    return frozenset(phrases)


def _translate_html(content, language):
    parser = _StaticTextTranslator(language)
    parser.feed(content)
    parser.close()
    return parser.result()


class PreferredLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = 'en'
        request.LANGUAGE_CODE = language
        translation.activate(language)
        response = self.get_response(request)
        if language not in ('en', 'en-gb') and response.get('Content-Type', '').startswith('text/html'):
            content = response.content.decode(response.charset or 'utf-8')
            response.content = _translate_html(content, language).encode(response.charset or 'utf-8')
            response['Content-Length'] = len(response.content)
        if response.get('Content-Type', '').startswith('text/html'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response
