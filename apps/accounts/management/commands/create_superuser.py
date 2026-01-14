"""
Management command to create a superuser from environment variables.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a superuser from environment variables'

    def handle(self, *args, **options):
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@invoicerecon.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not password:
            self.stderr.write(self.style.ERROR('DJANGO_SUPERUSER_PASSWORD environment variable is required'))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Superuser with email {email} already exists'))
            return

        user = User.objects.create_superuser(
            email=email,
            username=email,
            password=password,
        )
        user.is_firm_admin = True
        user.save()

        self.stdout.write(self.style.SUCCESS(f'Superuser created: {email}'))
