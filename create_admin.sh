#!/bin/bash

# Script to manage admin users in production database
# Uses production database at /var/lib/cloudsynk/db_prod.sqlite3

set -e

cd /home/utsingh/workspace/CloudSynk/

# Set up environment for production database
export DB_DIR="${DB_DIR:-/var/lib/cloudsynk}"
export BACKUP_DIR="${BACKUP_DIR:-/var/backups/cloudsynk}"

# Check if production environment is set up
if [ ! -d ".storage-env-prod" ]; then
    echo "❌ Production environment not found!"
    echo "Please run: sudo ./deploy_production.sh first"
    exit 1
fi

# Load environment variables from az_intf.systemd
load_environment() {
    if [ -f "/home/utsingh/workspace/az_intf.systemd" ]; then
        while IFS='=' read -r key value; do
            # Skip empty lines and comments
            [[ -z "$key" || "$key" =~ ^#.* ]] && continue
            # Remove surrounding quotes if present
            value="${value%\"}"
            value="${value#\"}"
            # Export the variable
            export "$key"="$value"
        done < /home/utsingh/workspace/az_intf.systemd
    else
        echo "❌ Environment file not found: /home/utsingh/workspace/az_intf.systemd"
        exit 1
    fi
}

# Ensure database directory exists with proper permissions
setup_database_dir() {
    sudo mkdir -p "$DB_DIR"
    sudo chown utsingh:utsingh "$DB_DIR"
}

# List all admin users
list_admins() {
    echo ""
    echo "=== Current Admin Users ==="
    echo ""
    load_environment
    
    .storage-env-prod/bin/python3 manage.py shell --settings=storage_webapp.settings_prod -c "
from django.contrib.auth.models import User
from django.conf import settings

print(f'Database: {settings.DATABASES[\"default\"][\"NAME\"]}')
print()

admins = User.objects.filter(is_superuser=True).order_by('username')

if not admins.exists():
    print('❌ No admin users found in the database.')
else:
    print(f'Found {admins.count()} admin user(s):')
    print()
    print(f'{\"ID\":<6} {\"Username\":<20} {\"Email\":<30} {\"Active\":<8} {\"Staff\":<8}')
    print('-' * 80)
    for admin in admins:
        active = '✅ Yes' if admin.is_active else '❌ No'
        staff = '✅ Yes' if admin.is_staff else '❌ No'
        print(f'{admin.id:<6} {admin.username:<20} {admin.email:<30} {active:<8} {staff:<8}')
"
    echo ""
}

# Delete an admin user
delete_admin() {
    echo ""
    echo "=== Delete Admin User ==="
    echo ""
    
    # First show current admins
    list_admins
    
    read -p "Enter username to delete (or 'cancel' to abort): " username
    
    if [ -z "$username" ] || [ "$username" = "cancel" ]; then
        echo "❌ Deletion cancelled."
        return
    fi
    
    echo ""
    read -p "⚠️  Are you sure you want to delete user '$username'? This cannot be undone! (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "❌ Deletion cancelled."
        return
    fi
    
    load_environment
    
    .storage-env-prod/bin/python3 manage.py shell --settings=storage_webapp.settings_prod -c "
from django.contrib.auth.models import User
from main.models import UserInfo
from django.conf import settings

username = '$username'

try:
    user = User.objects.get(username=username)
    
    # Check if this is the last admin
    admin_count = User.objects.filter(is_superuser=True).count()
    if admin_count <= 1 and user.is_superuser:
        print(f'❌ Cannot delete \"{username}\" - this is the last admin user!')
        print('   Create another admin user before deleting this one.')
    else:
        # Delete associated UserInfo if exists
        try:
            user_info = UserInfo.objects.get(user=user)
            user_info.delete()
            print(f'   - Deleted UserInfo for {username}')
        except UserInfo.DoesNotExist:
            pass
        
        # Delete the user
        user.delete()
        print(f'✅ Successfully deleted user \"{username}\"')
        print(f'   Database: {settings.DATABASES[\"default\"][\"NAME\"]}')
        
except User.DoesNotExist:
    print(f'❌ User \"{username}\" not found in database.')
except Exception as e:
    print(f'❌ Error deleting user: {e}')
"
    echo ""
}

# Create a new admin user
create_admin() {
    echo ""
    echo "=== Create Admin User ==="
    echo ""
    echo "📁 Using production database: $DB_DIR/db_prod.sqlite3"
    echo ""
    
    load_environment
    setup_database_dir
    
    # Get admin credentials from user
    read -p "Enter admin username: " username
    # Get admin credentials from user
    read -p "Enter admin username: " username
    if [ -z "$username" ]; then
        echo "❌ Error: Username cannot be empty"
        exit 1
    fi

    read -p "Enter admin email: " email
    if [ -z "$email" ]; then
        echo "❌ Error: Email cannot be empty"
        exit 1
    fi

    read -s -p "Enter admin password: " password
    echo ""
    if [ -z "$password" ]; then
        echo "❌ Error: Password cannot be empty"
        exit 1
    fi

    read -s -p "Confirm password: " password_confirm
    echo ""
    if [ "$password" != "$password_confirm" ]; then
        echo "❌ Error: Passwords do not match"
        exit 1
    fi

    echo ""
    echo "🔧 Running database migrations..."
    .storage-env-prod/bin/python3 manage.py migrate --settings=storage_webapp.settings_prod --noinput

    echo ""
    echo "👤 Creating admin user..."
    echo ""

    # Create admin user in production database
    .storage-env-prod/bin/python3 manage.py shell --settings=storage_webapp.settings_prod -c "
from django.contrib.auth.models import User
from main.models import UserInfo
from django.conf import settings

# Verify we're using the correct database
print(f'Database: {settings.DATABASES[\"default\"][\"NAME\"]}')
print()

username = '$username'
email = '$email'
password = '''$password'''

# Check if user already exists
if User.objects.filter(username=username).exists():
    print(f'⚠️  User \"{username}\" already exists.')
    user = User.objects.get(username=username)
    
    # Update password
    user.set_password(password)
    user.email = email
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.save()
    print(f'✅ Updated existing user \"{username}\"')
    print(f'   - Password updated')
    print(f'   - Email: {email}')
    print(f'   - Superuser privileges granted')
else:
    # Create new user
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    print(f'✅ Created new superuser \"{username}\"')
    print(f'   - Email: {email}')

# Create or update UserInfo
try:
    user_info = UserInfo.objects.get(user=user)
    print(f'   - UserInfo already exists')
except UserInfo.DoesNotExist:
    user_info = UserInfo.objects.create(
        user=user,
        subscription_type='OWNER',
        container_name=f'{username}-{email.split(\"@\")[0]}'
    )
    print(f'   - UserInfo created with OWNER subscription')

print()
print('=' * 60)
print('🎉 Admin user ready!')
print('=' * 60)
print(f'Username: {username}')
print(f'Email: {email}')
print(f'Database: {settings.DATABASES[\"default\"][\"NAME\"]}')
print()
print('You can now login at: http://cloudsynk.org.in/login/')
print('=' * 60)
"

    echo ""
    echo "✅ Admin user creation completed successfully!"
    echo ""
}

# Main menu
show_menu() {
    echo ""
    echo "╔════════════════════════════════════════════════╗"
    echo "║   CloudSynk Admin User Management             ║"
    echo "╚════════════════════════════════════════════════╝"
    echo ""
    echo "Database: $DB_DIR/db_prod.sqlite3"
    echo ""
    echo "Select an option:"
    echo "  1) Create new admin user"
    echo "  2) List all admin users"
    echo "  3) Delete an admin user"
    echo "  4) Exit"
    echo ""
    read -p "Enter your choice (1-4): " choice
    
    case $choice in
        1)
            create_admin
            ;;
        2)
            list_admins
            ;;
        3)
            delete_admin
            ;;
        4)
            echo ""
            echo "👋 Goodbye!"
            echo ""
            exit 0
            ;;
        *)
            echo ""
            echo "❌ Invalid option. Please choose 1-4."
            ;;
    esac
}

# Main loop
while true; do
    show_menu
done

