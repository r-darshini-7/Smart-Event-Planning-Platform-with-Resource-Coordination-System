"""
Management command: export_data
Export all event data to JSON or CSV format.

Usage:
  python manage.py export_data --model events --output events.json
  python manage.py export_data --model members --output members.csv --format csv
"""
import json
import csv
import sys
from django.core.management.base import BaseCommand
from django.core import serializers
from events.models import Event, EventMember, BudgetItem, Vendor, Venue


class Command(BaseCommand):
    help = 'Export event data to JSON or CSV'

    def add_arguments(self, parser):
        parser.add_argument('--model', type=str, default='events',
                            choices=['events', 'members', 'budget', 'vendors', 'venues'],
                            help='Which dataset to export')
        parser.add_argument('--format', type=str, default='json', choices=['json', 'csv'])
        parser.add_argument('--output', type=str, default='', help='Output file path (defaults to stdout)')

    def handle(self, *args, **options):
        model_name = options['model']
        fmt = options['format']
        output = options['output']

        model_map = {
            'events': Event,
            'members': EventMember,
            'budget': BudgetItem,
            'vendors': Vendor,
            'venues': Venue,
        }
        qs = model_map[model_name].objects.all()

        out = open(output, 'w', encoding='utf-8') if output else sys.stdout

        if fmt == 'json':
            out.write(serializers.serialize('json', qs, indent=2))
        else:  # csv
            if not qs.exists():
                self.stdout.write(self.style.WARNING('No data found.'))
                if output:
                    out.close()
                return
            fields = [f.name for f in qs.model._meta.concrete_fields]
            writer = csv.writer(out)
            writer.writerow(fields)
            for obj in qs:
                writer.writerow([getattr(obj, f) for f in fields])

        if output:
            out.close()
            self.stdout.write(self.style.SUCCESS(f'Exported {model_name} to {output}'))
