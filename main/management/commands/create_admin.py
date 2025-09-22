"""
Management command to create admin users for Django admin panel
Usage: python manage.py create_admin --username admin --email admin@cloudsynk.com
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from main.models import UserInfo
from main.subscription_config import SUBSCRIPTION_VALUES
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import getpass
import secrets
import string

class Command(BaseCommand):
    help = 'Create an admin user for the CloudSynk Django admin panel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            required=True,
            help='Username for the admin user'
        )
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='Email address for the admin user'
        )
        parser.add_argument(
            '--generate-password',
            action='store_true',
            help='Generate a secure random password'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        generate_password = options.get('generate_password', False)

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User "{username}" already exists.')

        # Handle password
        if generate_password:
            password = self.generate_secure_password()
            self.stdout.write(f"Generated secure password: {password}")
            self.stdout.write(self.style.WARNING("SAVE THIS PASSWORD SECURELY!"))
        else:
            password = getpass.getpass("Enter password for admin user: ")
            confirm_password = getpass.getpass("Confirm password: ")
            if password != confirm_password:
                raise CommandError("Passwords do not match.")

        # Validate password strength
        try:
            validate_password(password)
        except ValidationError as e:
            raise CommandError(f"Password validation failed: {'; '.join(e.messages)}")

        try:
            # Create admin user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=True,
                is_superuser=True,
                is_active=True,
            )

            # Create UserInfo with OWNER subscription (highest level)
            UserInfo.objects.create(
                user=user,
                user_name=username,
                subscription_type='OWNER',
                container_name=f"admin-{username.lower()}",
                storage_quota_bytes=SUBSCRIPTION_VALUES['OWNER'],
                storage_used_bytes=0,
                email_id=email,
            )

            self.stdout.write(
                self.style.SUCCESS(f'Successfully created admin user "{username}" with OWNER subscription')
            )
            
            self.stdout.write(
                f"Admin user can now access the Django admin panel at /admin/"
            )

        except Exception as e:
            raise CommandError(f'Failed to create admin user: {e}')

    def generate_secure_password(self, length=20):
        """Generate a secure random password with mixed characters"""
        # Ensure at least one character from each category
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        # Build password with at least one from each category
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill the rest randomly
        all_chars = lowercase + uppercase + digits + special
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)