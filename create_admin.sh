#!/bin/bash

# Simple script to create admin user using Django shell
cd /workspace/utsingh/CloudSynk

echo "Creating admin user through Django shell..."

sudo /workspace/utsingh/CloudSynk/.storage-env/bin/python manage.py shell -c "
from django.contrib.auth.models import User
from main.models import UserInfo
from main.subscription_config import SUBSCRIPTION_VALUES
import secrets
import string

# Generate secure password
def generate_password(length=20):
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = '!@#\$%^&*()_+-='
    
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]
    
    all_chars = lowercase + uppercase + digits + special
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))
    
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)

# Create admin user
username = 'cloudsynk_admin'
email = 'utkarsh0124@gmail.com'
password = generate_password()

print(f'Creating admin user: {username}')
print(f'Generated password: {password}')
print('SAVE THIS PASSWORD SECURELY!')

# Check if user exists
if User.objects.filter(username=username).exists():
    print(f'User {username} already exists. Skipping creation.')
else:
    # Create user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )
    
    # Create UserInfo
    UserInfo.objects.create(
        user=user,
        user_name=username,
        subscription_type='OWNER',
        container_name=f'admin-{username.lower()}',
        storage_quota_bytes=SUBSCRIPTION_VALUES['OWNER'],
        storage_used_bytes=0,
        email_id=email,
    )
    
    print(f'Successfully created admin user: {username}')
    print('Admin can now access Django admin at /admin/')
"