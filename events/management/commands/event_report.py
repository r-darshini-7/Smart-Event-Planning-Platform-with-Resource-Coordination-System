"""
Management command: event_report
Generate a text-based summary report for events.

Usage:
  python manage.py event_report [--status live] [--format csv]
  python manage.py event_report --export-file report.csv
"""
import csv
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from events.models import Event, EventMember, BudgetItem
from django.db.models import Sum, Count


class Command(BaseCommand):
    help = 'Generate event analytics report (console or CSV file)'

    def add_arguments(self, parser):
        parser.add_argument('--status', type=str, default='', help='Filter by event status (e.g. live, completed)')
        parser.add_argument('--format', type=str, default='table', choices=['table', 'csv'], help='Output format')
        parser.add_argument('--export-file', type=str, default='', help='Write CSV output to this file path')

    def handle(self, *args, **options):
        status_filter = options['status']
        output_format = options['format']
        export_file = options['export_file']

        qs = Event.objects.annotate(
            reg_count=Count('members'),
            total_proj=Sum('budget_items__projected_amount'),
            total_act=Sum('budget_items__actual_amount'),
        ).order_by('-start_time')

        if status_filter:
            qs = qs.filter(status=status_filter)

        rows = []
        for event in qs:
            rows.append({
                'UID': event.uid,
                'Title': event.title,
                'Status': event.get_status_display(),
                'Start': event.start_time.strftime('%Y-%m-%d'),
                'Registrations': event.reg_count,
                'Max Attendance': event.max_attendance,
                'Total Budget': str(event.total_budget),
                'Projected Expenses': str(event.total_proj or 0),
                'Actual Expenses': str(event.total_act or 0),
            })

        if export_file or output_format == 'csv':
            out = open(export_file, 'w', newline='', encoding='utf-8') if export_file else sys.stdout
            if rows:
                writer = csv.DictWriter(out, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            if export_file:
                out.close()
                self.stdout.write(self.style.SUCCESS(f'Report written to {export_file}'))
            return

        # Table output
        if not rows:
            self.stdout.write(self.style.WARNING('No events found.'))
            return

        col_widths = {k: max(len(k), max(len(str(r[k])) for r in rows)) for k in rows[0].keys()}
        header = '  '.join(k.ljust(col_widths[k]) for k in rows[0].keys())
        self.stdout.write(self.style.HTTP_INFO(header))
        self.stdout.write('-' * len(header))
        for row in rows:
            self.stdout.write('  '.join(str(row[k]).ljust(col_widths[k]) for k in row.keys()))
        self.stdout.write(f'\nTotal: {len(rows)} event(s)')
