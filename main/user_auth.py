from django.contrib.auth.models import User

def user_exists(username):
    try:
        User.objects.get(username=username)
    except User.DoesNotExist:
        return False 
    return True

def username_valid(username):
    return not(username==None or username=="")
