from django.core.management.base import BaseCommand
from myapp.models import Treasurer

class Command(BaseCommand):
    help = 'Create admin user'

    def handle(self, *args, **options):
        if not Treasurer.objects.filter(username='admin').exists():
            admin = Treasurer.objects.create_user(
                username='admin',
                email='admin@churchfund.com',
                password='admin123',
                first_name='Admin',
                last_name='User',
                is_staff=True,
                is_superuser=True,
                is_approved=True
            )
            self.stdout.write('Admin user created successfully!')
        else:
            self.stdout.write('Admin user already exists!')