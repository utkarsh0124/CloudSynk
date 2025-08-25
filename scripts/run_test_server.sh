#!/usr/bin/env bash
set -euo pipefail

echo "BASE_DIR : ${BASE_DIR}"

# optional overrides:
: "${ADMIN_USERNAME:=admin}"
: "${ADMIN_EMAIL:=admin@example.com}"
: "${ADMIN_PASSWORD:=root123}"
: "${DEV_SITE:=1}"   # set to 0 in environments where you don't want a localhost Site created
PORT=8000

cleanup_dev_site() {
    if [ "${DEV_SITE:-0}" = "1" ]; then
        echo "Cleaning up dev Site (localhost:8000)"
        python3 manage.py shell <<PY
from django.contrib.sites.models import Site
Site.objects.filter(domain='localhost:8000').delete()
PY
    fi
}

# ensure cleanup runs on exit (INT/TERM/EXIT)
trap cleanup_dev_site EXIT

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

# create dev Site row only when DEV_SITE=1
if [ "${DEV_SITE}" = "1" ]; then
  echo "Creating/updating dev Site (localhost:8000)"
  python3 manage.py shell <<PY
from django.contrib.sites.models import Site
Site.objects.update_or_create(id=1, defaults={'domain':'localhost:8000','name':'localhost'})
PY
fi

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
python3 manage.py runserver 127.0.0.1:8000 --noreload
