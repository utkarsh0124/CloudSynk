from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import auth
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from urllib3 import request
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
    else:
        return JsonResponse({'success': False, 'error': 'API Instantiation Failed', 'redirect': '/'}, status=500)
    return JsonResponse({'success': True, 'redirect': '/'}, status=200)

def user_signup(request):
    logger.log(severity['INFO'], 'SIGNUP')
    return JsonResponse({'success': True, 'redirect': '/'}, status=200)


def signup_auth(request):
    logger.log(severity['INFO'], 'SIGNUP AUTH')
    
    if request.method == 'POST':
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
    
        if password1 != password2:
           return JsonResponse({'success': False, 'error': 'Passwords do not match', 'redirect': 'signup/'}, status=400)
        if utils.user_exists(username):
            return JsonResponse({'success': False, 'error': 'Username already exists', 'redirect': 'signup/'}, status=400)

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
                # Add a Container for this new User
                api_instance.add_container(user)
                
                logger.log(severity['INFO'], 'USER CONTAINER CREATED FOR USER: {}'.format(username))
                return JsonResponse({'success': True, 'redirect': '/login/'}, status=200)
            else:
                #delete user if instantiation failed
                user.delete()
                user_info.delete()
                return JsonResponse({'success': False, 'error': 'API Instantiation Failed', 'redirect': '/'}, status=500)
        else:
            return JsonResponse({'success': False, 'error': 'User already exists', 'redirect': '/'}, status=400)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method', 'redirect': '/'}, status=400)


def user_login(request):
    logger.info('LOGIN')
    return render(request, 'user/login.html')


def login_auth(request):
    logger.log(severity['INFO'], 'LOGIN AUTH')

    if request.user.is_authenticated:        
        logger.log(severity['INFO'], 'User: {} already logged in'.format(request.user.username))
        return home(request)
    
    if request.method == 'POST':
        username = request.POST.get("username")
        password = request.POST.get("password")

        logger.log(severity['INFO'], 'USER:{} '.format(username))

        if not username or not password:
            return JsonResponse({'success': False, 'error': 'Missing username or password', 'redirect': '/'}, status=400)

        if not utils.username_valid(username):
            return JsonResponse({'success': False, 'error': 'Invalid username', 'redirect': '/'}, status=400)

        if utils.user_exists(username):
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return JsonResponse({'success': True, 'redirect': '/'})
            else:
                #Django authentication failed! Incorrect password
                return JsonResponse({'success': False, 'error': 'Invalid credentials', 'redirect': '/'}, status=400)
        else:
            #Django authentication failed! Incorrect password
            return JsonResponse({'success': False, 'error': 'Invalid credentials', 'redirect': '/'}, status=400)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method', 'redirect': '/'}, status=400)

@login_required
def user_logout(request):
    logger.log(severity['INFO'], 'LOGOUT USER {}'.format(request.user.username))
    if request.user.is_authenticated:
        auth.logout(request)
        # delete singleton object allocated for the user 
        api.del_api_instance()
        return home(request)
    return JsonResponse({'success': False, 'error': 'User not authenticated', 'redirect': '/'}, status=400)


@login_required
def add_blob(request):
    logger.log(severity['INFO'], 'ADD BLOB')
    user_info = UserInfo.objects.get(user=request.user)
    #get blob details from form
    if AZURE_API_DISABLE:
        #take the text value from the form
        uploaded_file = request.FILES.get("blob_file")
        file_name = request.GET.get('file_name')
    else:
        uploaded_file = request.FILES['blob_file']
        file_name = request.GET.get('file_name')

    logger.log(severity['INFO'], 'BLOB NAME : {}'.format(file_name))
    
    if file_name is None:
        return JsonResponse({'success': False, 'error': 'Missing file name', 'redirect': '/'}, status=400)

    logger.log(severity['INFO'], 'BLOB NAME : {}'.format(file_name))

    #get size of file to be uploaded
    file_size_bytes = 100
    
    #check if the new blob exceeds data_storage_limit
    if user_info.storage_used_bytes + file_size_bytes >= user_info.storage_quota_bytes:
        return JsonResponse({'success': False, 'error': 'Storage Exceeded! Upload Failed', 'redirect': '/'}, status=400)

    #update the total storage for this user in user_info DB
    user_info.storage_used_bytes += file_size_bytes
    
    api_instance = api.get_api_instance(request.user, user_info.container_name)
    if api_instance:
        api_instance.create_blob(file_name)
    else:
        return JsonResponse({'success': False, 'error': 'API Instantiation Failed', 'redirect': '/'}, status=500)
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
            user_info.storage_used_bytes -= api_instance.get_blob_size(blob_name)
            api_instance.delete_blob(blob_name)       
        else:
            return JsonResponse({'success': False, 'error': 'API Instantiation Failed', 'redirect': '/'}, status=500)
    return home(request)


@login_required
def home(request):
    logger.log(severity['INFO'], 'HOME')
    user_info = UserInfo.objects.filter(user=request.user).values()
    api_instance = api.get_api_instance(request.user, user_info[0]['container_name'])

    if user_info.count() != 0:
        blob_list = api_instance.list_blob()
        return render(
                    request, 
                    'main/sample.html', 
                    {
                        'blobQuery': blob_list,
                        'username': request.user.username,
                        'json_status': {'status': 'success'}
                    }
                )
    return JsonResponse({'success': False, 'error': 'User info not found', 'redirect': '/login/'}, status=400)