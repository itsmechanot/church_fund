import os
from django.core.management.base import BaseCommand
from myapp.models import Treasurer

class Command(BaseCommand):
    help = 'Create admin user from environment variables'

    def handle(self, *args, **options):
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        email = os.environ.get('ADMIN_EMAIL', 'admin@churchfund.com')
        
        if not Treasurer.objects.filter(username=username).exists():
            admin = Treasurer.objects.create(
                username=username,
                email=email,
                first_name='Admin',
                last_name='User',
                is_staff=True,
                is_superuser=True,
                is_approved=True,
                is_active=True
            )
            admin.set_password(password)
            admin.save()
            self.stdout.write(f'Admin user {username} created successfully!')
        else:
            # Update existing admin password
            admin = Treasurer.objects.get(username=username)
            admin.set_password(password)
            admin.save()
            self.stdout.write(f'Admin user {username} password updated!')