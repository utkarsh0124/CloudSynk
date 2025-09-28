#!/bin/bash

# Simple script to create admin user using Django shell
cd /workspace/utsingh/CloudSynk

echo "=== CloudSynk Admin User Creation ==="
echo ""

# Get username from user input
read -p "Enter admin username: " username
if [ -z "$username" ]; then
    echo "Error: Username cannot be empty"
    exit 1
fi

# Get email from user input
read -p "Enter admin email: " email
if [ -z "$email" ]; then
    echo "Error: Email cannot be empty"
    exit 1
fi

echo ""
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
username = '$username'
email = '$email'
password = generate_password()

print(f'Creating admin user: {username}')
print(f'Email: {email}')
print(f'Generated password: {password}')
print('')
print('⚠️  SAVE THIS PASSWORD SECURELY! ⚠️')
print('=' * 50)

# Check if user exists
if User.objects.filter(username=username).exists():
    print(f'❌ User {username} already exists. Skipping creation.')
    print('If you need to reset the password, delete the user first or use a different username.')
else:
    try:
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
        
        print(f'✅ Successfully created admin user: {username}')
        print(f'📧 Email: {email}')
        print(f'🔑 Password: {password}')
        print(f'📦 Subscription: OWNER (1 TB storage)')
        print('')
        print('The admin user can now:')
        print('  - Access the custom admin panel at: http://your-domain.com/')
        print('  - Manage users and subscriptions')
        print('  - View system statistics')
        print('')
        print('⚠️  Remember to save the password in a secure location!')
        
    except Exception as e:
        print(f'❌ Error creating admin user: {e}')
"

echo ""
echo "Admin user creation process completed."