from django.contrib.auth.models import User

def assign_container(username):
    # Logic to create new Container name for a New User
    container_name = username + "_container"
    print("NEW Container Name : ", container_name)
    return container_name

def user_exists(username):
    try:
        User.objects.get(username=username)
        print("User list : ", User.objects.all())
    except User.DoesNotExist:
        return False 
    return True

def username_valid(username):
    return not(username==None or username=="")
