#!/usr/bin/env bash
set -euo pipefail

# optional overrides:
: "${ADMIN_USERNAME:=admin}"
: "${ADMIN_EMAIL:=admin@example.com}"
: "${ADMIN_PASSWORD:=root123}"
PORT=8000

logout_user_session() {
    echo "Logging out all users from earlier session"
    python3 manage.py shell <<EOF
from django.contrib.sessions.models import Session
Session.objects.all().delete()
EOF
}

python3 manage.py makemigrations
if [ $? -ne 0 ]; then
    echo "FAILED at makemigrations"
    exit 1
fi

rm -rf log/*

python3 manage.py migrate

# create superuser if none with that username & is_superuser exists
python3 manage.py shell <<PY
from django.contrib.auth import get_user_model
User = get_user_model()
username = "${ADMIN_USERNAME}"
email = "${ADMIN_EMAIL}"
password = "${ADMIN_PASSWORD}"
if not User.objects.filter(username=username, is_superuser=True).exists():
    print("Creating superuser:", username)
    User.objects.create_superuser(username=username, email=email, password=password)
else:
    print("Superuser already exists:", username)
PY

# now start the server (no autoreload)
logout_user_session
python3 manage.py runserver --noreload
