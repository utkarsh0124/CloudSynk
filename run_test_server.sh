#!/bin/bash

logout_user_session() {
    echo "Logging out all users from earlier session"
    
    python manage.py shell <<EOF
from django.contrib.sessions.models import Session
Session.objects.all().delete()
EOF
}

logout_user_session

python3 manage.py makemigrations
if [ $? -ne 0 ]; then
    echo "FAILED at makemigrations"
    exit 1
fi
rm -rf log/*
python3 manage.py migrate && python3 manage.py runserver --noreload
