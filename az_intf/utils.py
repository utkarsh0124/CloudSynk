from django.contrib.auth.models import User
from django import forms
from django.core.exceptions import ValidationError

def assign_container(username):
    # Logic to create new Container name for a New User
    container_name = username + "-container"
    return container_name


def user_exists(username):
    try:
        User.objects.get(username=username)
    except User.DoesNotExist:
        return False 
    return True


def username_valid(username):
    return not(username==None or username=="")


def validate_file_extension(value):
    import os
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.png', '.xlsx', '.xls', 'txt', 'zip']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension.')
