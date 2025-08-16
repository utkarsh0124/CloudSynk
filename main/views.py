from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import auth, messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .subscription_config import SUBSCRIPTION_CHOICES, SUBSCRIPTION_VALUES
from storage_webapp.settings import DEFAULT_SUBSCRIPTION_AT_INIT

from az_intf import api
from .models import UserInfo
from az_intf import utils

from storage_webapp import logger, severity
from apiConfig import AZURE_API_DISABLE

@login_required
def remove_user(request):
    usr_obj = request.user
    auth.logout(request)
    
    user_info = UserInfo.objects.get(user=usr_obj)

    api_instance = api.get_api_instance(request.user, user_info.container_name)
    if api_instance:
        # delete container handles deleting user
        api_instance.delete_container()

        api.del_api_instance()

        ret_str = "<h1>User Removed</h1>"
    else:
        return HttpResponse("<h1>API Instantiation Failed</h1>")
    return HttpResponse(ret_str)


def user_signup(request):
    logger.log(severity['INFO'], 'SIGNUP')
    return render(request, 'user/signup.html')


def signup_auth(request):
    logger.log(severity['INFO'], 'SIGNUP AUTH')
    return_str = '<H1>USER SIGNUP COMPLETED </H1>'  
    
    if request.method == 'POST':
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
    
        if password1 != password2:
           return HttpResponse("<h1>Passwords dos not match</h1>")
        if utils.user_exists(username):
            return HttpResponse("<h1>Username already exists</h1>")

        print('API Instance created for user:', username)
        user = User.objects.create_user(username=username,password=password1)
        user.save()
        user_info, created = UserInfo.objects.get_or_create(
            user=user,
            defaults = {
                'user_name': username,
                'subscription_type': dict(SUBSCRIPTION_CHOICES)[DEFAULT_SUBSCRIPTION_AT_INIT],  # Default subscription type
                'container_name': utils.assign_container(username),
                'storage_quota_bytes': dict(SUBSCRIPTION_VALUES)[DEFAULT_SUBSCRIPTION_AT_INIT],  # Default storage quota
                'storage_used_bytes': 0,  # Default storage used
                'dob' : None,
                'email_id' : request.POST.get("email_id")
            }
        )
        if created:
            api_instance = api.get_api_instance(user, utils.assign_container(username))
            if api_instance:
                print('User created:', user)
                # Add a Container for this new User
                api_instance.add_container(user)
                
                logger.log(severity['INFO'], 'USER CONTAINER CREATED FOR USER: {}'.format(username))
                return redirect(to='/login/')    
            else:
                #delete user if instantiation failed
                user.delete()
                user_info.delete()
                return HttpResponse("<h1>API Instantiation Failed</h1>")
        else:
            return HttpResponse("<h1>User already exists</h1>")
    else:
        return_str = "<h1>Try request.POST</h1>"
    return HttpResponse(return_str)


def user_login(request):
    logger.info('LOGIN')
    return render(request, 'user/login.html')


def login_auth(request):
    logger.log(severity['INFO'], 'LOGIN AUTH')
    return_str = '<H1>LOGIN FAILED PLEASE RELOAD AND TRY AGAIN</H1>'
    
    if request.user.is_authenticated:
        logger.log(severity['INFO'], 'User already Logged in')
        return redirect("/")
    
    if request.method == 'POST':
        username = request.POST.get("username")
        password = request.POST.get("password")

        logger.log(severity['INFO'], 'USER:{} '.format(username))

        if not utils.username_valid(username):
            return HttpResponse("<h1>Username Not Found</h1>")
        
        if utils.user_exists(username):
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


@login_required
def user_logout(request):
    logger.log(severity['INFO'], 'LOGOUT USER {}'.format(request.user.username))
    if request.user.is_authenticated:
        auth.logout(request)

        # delete singleton object allocated for the user 
        api.del_api_instance()
        return HttpResponse("<H1>User logged out</H1>")
    return redirect('/')


@login_required
def add_blob(request):
    logger.log(severity['INFO'], 'ADD BLOB')
    user_info = UserInfo.objects.get(user=request.user)
    #get blob details from form
    if AZURE_API_DISABLE:
        #take the text value from the form
        uploaded_file = request.FILES.get("blob_file")
        filename = uploaded_file.name
    else:
        uploaded_file = request.FILES['blob_file']
        filename = uploaded_file.name
    
    logger.log(severity['INFO'], 'BLOB NAME : {}'.format(filename))

    #get size of file to be uploaded
    file_size_kb = 100
    
    #check if the new blob exceeds data_storage_limit
    if user_info.total_storage_size_kb + file_size_kb >= user_info.storage_quota_kb:
        return HttpResponse("<h1>Storage Exceeded!<br>UPLOAD FAILED</h1>")    
    
    #update the total storage for this user in user_info DB
    user_info.total_storage_size_kb += file_size_kb
    
    api_instance = api.get_api_instance(request.user, user_info.container_name)
    if api_instance:
        api_instance.create_blob(uploaded_file, filename)
    else:
        return HttpResponse("<h1>API Instantiation Failed</h1>")
    return home(request)


@login_required
def delete_blob(request, blob_name):
    logger.log(severity['INFO'], 'DELETE BLOB')
    if request.method == 'POST':
        logger.log(severity['INFO'], 'BLOB NAME : {}'.format(blob_name))
        
        #update total size in User Info DB
        user_info = UserInfo.objects.get(user=request.user)
        
        #delete from Blob DB
        api_instance = api.get_api_instance(request.user, user_info.container_name)
        if api_instance:
            user_info.total_storage_size_kb -= api_instance.get_blob_size(blob_name)
            api_instance.delete_blob(blob_name)       
        else:
            return HttpResponse("<h1>API Instantiation Failed</h1>")
    return home(request)


@login_required
def home(request):
    logger.log(severity['INFO'], 'HOME')

    if request.user.username != 'admin':
        user_info = UserInfo.objects.filter(user=request.user).values()
        api_instance = api.get_api_instance(request.user, user_info[0]['container_name'])

        if user_info.count() != 0:
            blob_list = api_instance.list_blob()
            return render(
                request, 
                'main/sample.html', 
                {
                    'blobQuery' : blob_list,
                    'username': request.user.username
                }
            )
        else:
            return HttpResponse("<h1>User container not found</h1>")
    return redirect('login/')