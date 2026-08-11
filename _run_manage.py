"""Helper script to run manage.py commands from within the event_management workspace."""
import sys
import os

# The Django project root (parent of this workspace) contains the event_management package
parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent not in sys.path:
    sys.path.insert(0, parent)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'event_management.settings')

from django.core.management import execute_from_command_line
execute_from_command_line(sys.argv)
