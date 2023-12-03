from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse

from . import operations
from .user_auth import user_exists, username_valid
from .models import UserInfo
from django.contrib import auth, messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

# import json

def user_signup(request):
    return render(request, 'user/signup.html')

def signup_auth(request):
    return_str = '<H1>USER SIGNUP COMPLETED </H1>'  
    
    if request.method == 'POST':
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
    
        #Passowrds do not match
        if password1 != password2:
           return HttpResponse("<h1>Passwords does not match</h1>")
        
        #username taken
        if user_exists(username):
            return HttpResponse("<h1>Username already exists</h1>")
        
        user = User.objects.create_user(username=username,password=password1)
        user.save()
        
        #get container id from backend
        container_id = operations.assign_container(username)
        
        #assign storage quota based on user_type
        #standard user - 5GB, Premium user - 10GB
        storage_quota_kb = 4883000 #5GB
        
        user_info = UserInfo.objects.create(
            container_id=container_id, 
            user_type="REGULAR",
            storage_quota_kb=storage_quota_kb,
            total_storage_size_kb=0)
        
        user_info.user = user
        user_info.save()
                
        return redirect(to='/login/')    
    else:
        return_str = "<h1>Try request.POST</h1>"
        return HttpResponse(return_str)

def user_login(request):
    return render(request, 'user/login.html')

def login_auth(request):
    return_str = '<H1>LOGIN FAILED PLEASE RELOAD AND TRY AGAIN</H1>'
    
    if request.user.is_authenticated:
        return_str = '<H1>User already Logged in</H1>'
        return HttpResponse(return_str)
    
    if request.method == 'POST':
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        if not username_valid(username):
            return HttpResponse("<h1>Invalid Username</h1>")
        
        if request.user.is_authenticated:
            return HttpResponse("<H1>User Already Signed IN</H1>")
        
        if user_exists(username):
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                return redirect('/')
            else:
                # No backend authenticated the credentials
                return redirect('/signup/')
        else:
            return HttpResponse("<h1>Invalid Username</h1>")
    return HttpResponse(return_str)
 
def user_logout(request):
    if request.user.is_authenticated:
        auth.logout(request)
        return HttpResponse("<H1>User logged out</H1>")
    return redirect('/')

def add_blob(request):
    #get container id from user
    container_id = UserInfo.objects.get(user=request.user).container_id
    
    #get blob details from form
    filename = request.POST.get("filename")
    print("\n\nAdding : ", filename, "\n\n")
    file_size_kb = 100
    
    #check if the new blob exceeds data_storage_limit
    user_info = UserInfo.objects.get(user=request.user)
    if  user_info.total_storage_size_kb + file_size_kb >= user_info.storage_quota_kb:
        return HttpResponse("<h1>Storage Exceeded</h1>")    
    
    #update the total storage for this user in user_info DB
    user_info.total_storage_size_kb += file_size_kb

    #update blob DB
    status = operations.add_file(filename, container_id)
    print("ADDITION SUCCESS : ", bool(status))
    return home(request)

def delete_blob(request):
    if request.method == 'GET':
        # blob_name = json.loads(request.GET.get('blob_name'))
        blob_name = request.GET.get('blob_name')
        
        #update total size in User Info DB
        user_info = UserInfo.objects.get(user=request.user)
        user_info.total_storage_size_kb -= operations.get_blob_size(blob_name)
        
        #delete from Blob DB
        operations.delete_file(blob_name)
        print("BLOB name : ", blob_name)
    return home(request)

@login_required
def home(request):
    print("\n user : ", request, '\n')
    if request.user.username != 'admin':
        #get blob list from az_intf
        user_info = UserInfo.objects.filter(user=request.user).values()
        if user_info.count() != 0:
            blob_list = operations.list_files(user_info[0]['container_id'])
            for blob in blob_list:
                print("\n\nblob list : ", blob_list, "\n\n")
            return render(request, 'main/home.html', {'blobQuery' : blob_list})
        else:
            return HttpResponse("<h1>User container not found</h1>")
    return redirect('login/')