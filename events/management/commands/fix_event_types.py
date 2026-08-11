from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Infer and update event_type and subcategory from category names for existing events.'

    def handle(self, *args, **options):
        from events.models import Event

        keywords = {
            'hackathon': 'hackathons',
            'hack': 'hackathons',
            'tech': 'techfest',
            'cultur': 'cultural',
            'competition': 'competitions',
            'comp': 'competitions',
            'seminar': 'seminar',
        }

        def infer(name):
            if not name:
                return None
            n = name.lower()
            for k, v in keywords.items():
                if k in n:
                    return v
            return None

        updated = []
        qs = Event.objects.filter(event_type='others')
        for e in qs:
            cat = getattr(e, 'category', None)
            if cat and getattr(cat, 'name', None):
                inferred = infer(cat.name)
                if inferred:
                    e.event_type = inferred
                    e.subcategory = cat.name
                    e.save()
                    updated.append(e.pk)

        self.stdout.write(f'Updated {len(updated)} events: {updated}')
