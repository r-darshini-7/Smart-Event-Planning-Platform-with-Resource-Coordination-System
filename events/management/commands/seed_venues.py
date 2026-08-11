"""
Management command: seed_venues
Seed sample venue and resource data for development/testing.

Usage:
  python manage.py seed_venues
"""
from django.core.management.base import BaseCommand
from events.models import Venue, Resource, Vendor


class Command(BaseCommand):
    help = 'Seed sample venue, resource, and vendor data'

    def handle(self, *args, **options):
        venues = [
            {'name': 'Main Auditorium', 'city': 'Chennai', 'capacity': 1000, 'hourly_rate': 5000, 'status': 'available'},
            {'name': 'Conference Hall A', 'city': 'Chennai', 'capacity': 200, 'hourly_rate': 1500, 'status': 'available'},
            {'name': 'Open Air Amphitheatre', 'city': 'Chennai', 'capacity': 500, 'hourly_rate': 2000, 'status': 'available'},
        ]
        for v in venues:
            obj, created = Venue.objects.get_or_create(name=v['name'], defaults=v)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created venue: {obj.name}'))
            else:
                self.stdout.write(f'Venue exists: {obj.name}')

        resources = [
            {'name': 'Projector', 'resource_type': 'equipment', 'quantity': 5, 'unit_cost': 200},
            {'name': 'Microphone Set', 'resource_type': 'equipment', 'quantity': 10, 'unit_cost': 100},
            {'name': 'Event Van', 'resource_type': 'transport', 'quantity': 2, 'unit_cost': 1500},
            {'name': 'Stage Lights', 'resource_type': 'equipment', 'quantity': 20, 'unit_cost': 300},
            {'name': 'Round Tables', 'resource_type': 'furniture', 'quantity': 50, 'unit_cost': 50},
        ]
        for r in resources:
            obj, created = Resource.objects.get_or_create(name=r['name'], defaults=r)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created resource: {obj.name}'))
            else:
                self.stdout.write(f'Resource exists: {obj.name}')

        vendors = [
            {'name': 'FreshFood Caterers', 'service_type': 'catering', 'contact_person': 'Ravi Kumar'},
            {'name': 'SpeedLogistics', 'service_type': 'logistics', 'contact_person': 'Priya S'},
            {'name': 'TechSupport Pro', 'service_type': 'it_support', 'contact_person': 'Anand R'},
            {'name': 'SnapShots Photography', 'service_type': 'photography', 'contact_person': 'Meena J'},
        ]
        for v in vendors:
            obj, created = Vendor.objects.get_or_create(name=v['name'], defaults=v)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created vendor: {obj.name}'))
            else:
                self.stdout.write(f'Vendor exists: {obj.name}')

        self.stdout.write(self.style.SUCCESS('Seeding complete.'))
