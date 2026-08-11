from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
import secrets

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser with a generated password and print the credentials'

    def add_arguments(self, parser):
        parser.add_argument('--username', '-u', type=str, help='Username for the superuser')
        parser.add_argument('--email', '-e', type=str, help='Email for the superuser')

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email')
        if not username and not email:
            raise CommandError('Provide at least --username or --email')

        if not username and email:
            username = email.split('@')[0]

        # ensure unique username
        base = username
        counter = 0
        while User.objects.filter(username=username).exists():
            counter += 1
            username = f"{base}{counter}"

        password = secrets.token_urlsafe(12)
        User.objects.create_superuser(username=username, email=email or '', password=password)

        self.stdout.write(self.style.SUCCESS('Superuser created'))
        self.stdout.write(f'Username: {username}')
        if email:
            self.stdout.write(f'Email: {email}')
        self.stdout.write(f'Password: {password}')
*** End Patch