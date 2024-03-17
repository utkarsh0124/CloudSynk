from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse

from az_intf import api
# from .user_auth import user_exists, username_valid
from .models import UserInfo
from django.contrib import auth, messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
# import json


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

def user_signup(request):
    return render(request, 'user/signup.html')

def signup_auth(request):
    return_str = '<H1>USER SIGNUP COMPLETED </H1>'  
    
    if request.method == 'POST':
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
    
        if password1 != password2:
           return HttpResponse("<h1>Passwords does not match</h1>")
        
        if user_exists(username):
            return HttpResponse("<h1>Username already exists</h1>")
    
        # User is new. Create new Api object
        api_instance = api.get_api_instance(assign_container(username))

        user = User.objects.create_user(username=username,password=password1)
        user.save()
    
        # Add a Container for this new User
        api_instance.add_container(user)
            
        return redirect(to='/login/')    
    else:
        return_str = "<h1>Try request.POST</h1>"
    return HttpResponse(return_str)

def user_login(request):
    return render(request, 'user/login.html')

def login_auth(request):
    return_str = '<H1>LOGIN FAILED PLEASE RELOAD AND TRY AGAIN</H1>'
    
    if request.user.is_authenticated:
        #User already Logged in
        return redirect("/")
    
    if request.method == 'POST':
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        if not username_valid(username):
            return HttpResponse("<h1>Username Not Found</h1>")
        
        if user_exists(username):
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                return redirect('/')
            else:
                #Django authentication failed
                return HttpResponse("<h1>Incorrect Password</h1>")
        else:
            return HttpResponse("<h1>Invalid Username</h1>")
    return HttpResponse(return_str)
 
def user_logout(request):
    if request.user.is_authenticated:
        auth.logout(request)

        # delete singleton object allocated for the user 
        api_instance = api.del_api_instance()
        return HttpResponse("<H1>User logged out</H1>")
    return redirect('/')

def add_blob(request):
    user_info = UserInfo.objects.get(user=request.user)
    
    #get blob details from form
    filename = request.POST.get("filename")
    print("\n\nAdding : ", filename, "\n\n")
    #get size of file to be uploaded
    file_size_kb = 100
    
    #check if the new blob exceeds data_storage_limit
    if user_info.total_storage_size_kb + file_size_kb >= user_info.storage_quota_kb:
        return HttpResponse("<h1>Storage Exceeded!<br>UPLOAD FAILED</h1>")    
    
    #update the total storage for this user in user_info DB
    user_info.total_storage_size_kb += file_size_kb
    
    api_instance = api.get_api_instance(user_info.container_name)
    api_instance.create_blob(filename)

    return home(request)

def delete_blob(request):
    if request.method == 'GET':
        # blob_name = json.loads(request.GET.get('blob_name'))
        blob_name = request.GET.get('blob_name')
        
        #update total size in User Info DB
        user_info = UserInfo.objects.get(user=request.user)
        
        #delete from Blob DB
        api_instance = api.get_api_instance(user_info.container_name)
        user_info.total_storage_size_kb -= api_instance.get_blob_size(blob_name)
        api_instance.delete_blob(blob_name)
       
        print("BLOB name : ", blob_name)
    return home(request)

@login_required
def home(request):    
    print("\n user : ", request, '\n')

    if request.user.username != 'admin':
        user_info = UserInfo.objects.filter(user=request.user).values()
        api_instance = api.get_api_instance(user_info[0]['container_name'])

        if user_info.count() != 0:
            blob_list = api_instance.list_blob()

            # print("Blob List : ")
            # for _blob in blob_list:
            #     print(_blob.blob_name)
                
            return render(request, 'main/home.html', {'blobQuery' : blob_list})
        else:
            return HttpResponse("<h1>User container not found</h1>")
    return redirect('login/')