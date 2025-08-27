from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect
from .serializers import UserSerializer
from az_intf import utils as app_utils
from az_intf import api as az_api
from .models import UserInfo
from storage_webapp.settings import DEFAULT_SUBSCRIPTION_AT_INIT
from .subscription_config import SUBSCRIPTION_CHOICES, SUBSCRIPTION_VALUES
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from django.conf import settings
from apiConfig import AZURE_API_DISABLE
from datetime import datetime


def _is_api_request(request):
    """Return True if the request should be treated as an API/XHR call returning JSON.

    Centralize content-negotiation to avoid brittle repeated checks.
    """
    accept = request.META.get('HTTP_ACCEPT', '')
    content_type = request.META.get('CONTENT_TYPE', '') or getattr(request, 'content_type', '') or ''
    auth_hdr = (request.META.get('HTTP_AUTHORIZATION') or '')
    return (
        'application/json' in accept
        or 'application/json' in content_type
        or auth_hdr.startswith('Token ')
        or auth_hdr.startswith('Bearer ')
        or request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    )



class SignupAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return render(request, 'user/signup.html')

    def post(self, request):
        
        # accept legacy form keys used by tests and template views
        data = request.data.copy()
        # support password1/password2 from form posts
        if 'password' not in data and 'password1' in data:
            data['password'] = data.get('password1')
        # allow email_id as alias for email
        if 'email' not in data and 'email_id' in data:
            data['email'] = data.get('email_id')

        serializer = UserSerializer(data=data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        email = serializer.validated_data.get('email')

        # basic password matching if given via password/confirm
        password2 = request.data.get('password2')
        if password2 and password2 != password:
            return Response({'success': False, 'error': 'Passwords do not match'}, status=status.HTTP_400_BAD_REQUEST)

        if app_utils.user_exists(username):
            return Response({'success': False, 'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.create({'username': username, 'password': password, 'email': email})

        user_info, created = UserInfo.objects.get_or_create(
            user=user,
            defaults={
                'user_name': username,
                'subscription_type': dict(SUBSCRIPTION_CHOICES)[DEFAULT_SUBSCRIPTION_AT_INIT],
                'container_name': app_utils.assign_container(username),
                'storage_quota_bytes': dict(SUBSCRIPTION_VALUES)[DEFAULT_SUBSCRIPTION_AT_INIT],
                'storage_used_bytes': 0,
                'dob': None,
                'email_id': request.data.get('email_id', email)
            }
        )

        if created:
            api_instance = az_api.get_api_instance(user, app_utils.assign_container(username))
            if api_instance:
                api_instance.add_container(user)
            else:
                user.delete()
                user_info.delete()
            # If the request came from a browser/form, redirect to the login page (render if you prefer)
            if not _is_api_request(request):
                return redirect('/login/')  # or render(request, 'user/signup_success.html', {'user': user})

            # Otherwise return JSON for API clients
            return Response({'success': True, 'user_id': user.id}, status=status.HTTP_201_CREATED)

        return Response({'success': True, 'user_id': user.id}, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # If already logged in, go to home
        if request.user and request.user.is_authenticated:
            return redirect('home')
        return render(request, 'user/login.html')

    def post(self, request):
        
        username = request.data.get('username') or request.POST.get('username')
        password = request.data.get('password') or request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)  # creates session cookie for session auth
            # Session-based auth: do not create or return tokens

            # treat JSON or XHR as API client
            is_api_client = _is_api_request(request)

            if not is_api_client:
                # browser/form -> redirect to home
                return redirect('home')
            # API client -> return JSON success (session cookie is set)
            return Response({'success': True}, status=status.HTTP_200_OK)

        return Response({'success': False, 'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # already authenticated -> go home
        if request.user and request.user.is_authenticated:
            return redirect('/home/')  
        # render the login page template (create main/templates/main/login.html)
        return render(request, 'main/login.html')

    def post(self, request):
        
        logout(request)
        az_api.del_api_instance()

        if not _is_api_request(request):
            return redirect('/home/')  
        # Otherwise return JSON for API clients
        return Response({'success': True}, status=status.HTTP_200_OK)


class DeactivateUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        usr_obj = request.user
        try:
            user_info = UserInfo.objects.get(user=usr_obj)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_api_instance(usr_obj, user_info.container_name)
        if api_instance:
            api_instance.delete_container()
            az_api.del_api_instance()
            # Delete the user
            usr_obj.delete()
            logout(request)
            if not _is_api_request(request):
                return redirect('login')
            return Response({'success': True, 'message': 'Account deactivated.'}, status=status.HTTP_200_OK)
        return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddBlobAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            user_info = UserInfo.objects.get(user=user)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        # file_name may come in form-data or JSON
        file_name = request.data.get('file_name') or request.query_params.get('file_name')
        if not file_name:
            return Response({'success': False, 'error': 'Missing file name'}, status=status.HTTP_400_BAD_REQUEST)

        # For simplicity, assume fixed file size as in original views
        file_size_bytes = 100
        if user_info.storage_used_bytes + file_size_bytes >= user_info.storage_quota_bytes:
            return Response({'success': False, 'error': 'Storage Exceeded! Upload Failed'}, status=status.HTTP_400_BAD_REQUEST)

        user_info.storage_used_bytes += file_size_bytes
        user_info.save()

        api_instance = az_api.get_api_instance(user, user_info.container_name)
        if api_instance:
            api_instance.create_blob(file_name)
            accept = request.META.get('HTTP_ACCEPT', '')
            content_type = request.META.get('CONTENT_TYPE', '')
            is_html_client = 'text/html' in accept or content_type.startswith('application/x-www-form-urlencoded') or 'multipart/form-data' in content_type
            if is_html_client:
                return redirect('/home/')  
        return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteBlobAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, blob_name=None):
        user = request.user
        try:
            user_info = UserInfo.objects.get(user=user)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_api_instance(user, user_info.container_name)
        if api_instance:
            size = api_instance.get_blob_size(blob_name)
            user_info.storage_used_bytes = max(0, user_info.storage_used_bytes - size)
            user_info.save()
            api_instance.delete_blob(blob_name)
            
            if not _is_api_request(request):
                return redirect('/home/')

        return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HomeAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        
        user = request.user
        # Redirect unauthenticated users to Login view
        if not request.user or not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)

        user_info_qs = UserInfo.objects.filter(user=user).values()
        if user_info_qs.count() == 0:
            return Response({'success': False, 'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_api_instance(user, user_info_qs[0]['container_name'])
        blob_list = api_instance.list_blob() if api_instance else []

        # convert numeric uploaded_at to datetime for the template
        for b in blob_list:
            ts = b.get('uploaded_at')
            try:
                b['uploaded_at_dt'] = datetime.fromtimestamp(float(ts)) if ts is not None else None
            except Exception:
                b['uploaded_at_dt'] = None

        # Decide whether to return JSON (API client) or render HTML (browser)
        if _is_api_request(request):
            return Response({'success': True, 'blobs': blob_list, 'username': user.username}, status=status.HTTP_200_OK)

        # render HTML for normal browser navigation
        context = {'success': True, 'blobs': blob_list, 'username': user.username}
        return render(request, 'main/sample.html', context)