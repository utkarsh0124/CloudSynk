from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from .serializers import UserSerializer
from az_intf.api_utils import utils as app_utils
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
        data = request.data.copy()
        if 'username' not in data:
            return Response({'success': False, 'error': 'Username is a required field'}, status=status.HTTP_400_BAD_REQUEST)
        if 'password1' not in data or 'password2' not in data:
            return Response({'success': False, 'error': 'Password Fields are required'}, status=status.HTTP_400_BAD_REQUEST)
        if data.get('password1') != data.get('password2'):
            return Response({'success': False, 'error': 'Passwords Do Not Match'}, status=status.HTTP_400_BAD_REQUEST)
        if 'email' not in data:
            return Response({'success': False, 'error': 'Email is a required field'}, status=status.HTTP_400_BAD_REQUEST)

        data['password'] = data.get('password1')
        data['email'] = data.get('email')

        serializer = UserSerializer(data=data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        email = serializer.validated_data.get('email')

        if app_utils.user_exists(username):
            return Response({'success': False, 'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.create({'username': username, 'password': password, 'email': email})

        created = az_api.init_container(user, username, app_utils.assign_container(username), email)
        if not created:
            return Response({'success': False, 'error': 'Container Initialization Failed'}, status=status.HTTP_400_BAD_REQUEST)

        container_instance = az_api.get_container_instance(username)
        if container_instance is None:
            user.delete()
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # If the request came from a browser/form, redirect to the login page (render if you prefer)
        if not _is_api_request(request):
            return redirect('/login/')  # or render(request, 'user/signup_success.html', {'user': user})

        # Otherwise return JSON for API clients
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

            if not _is_api_request(request):
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
        if not az_api.del_container_instance(request.user.username):
            return Response({'success': False, 'error': 'Error deleting container instance'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not _is_api_request(request):
            return redirect('/home/')  
        # Otherwise return JSON for API clients
        return Response({'success': True}, status=status.HTTP_200_OK)


class DeactivateUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        usr_obj = request.user
        api_instance = az_api.get_container_instance(usr_obj.username)
        if api_instance:
            api_instance.container_delete(usr_obj)
            az_api.del_container_instance(usr_obj.username)
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
        blob_file = request.data.get('blob_file') or request.query_params.get('blob_file')
        if not blob_file:
            return Response({'success': False, 'error': 'Missing blob file'}, status=status.HTTP_400_BAD_REQUEST)
        
        file_name = request.data.get('file_name') or request.query_params.get('file_name')
        if not file_name:
            return Response({'success': False, 'error': 'Missing file name'}, status=status.HTTP_400_BAD_REQUEST)

        uploaded = request.FILES.get('blob_file')
        if not uploaded:
            # handle error
            return Response({'success': False, 'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        # For simplicity, assume fixed file size as in original views
        file_size_bytes = 100

        api_instance = az_api.get_container_instance(user_info.user_name)
        if api_instance:
            # upload_sas_url = api_instance.get_blob_sas_url(blob_id, permission='w', expiry_hours=1)
            # if not upload_sas_url:
            #     return Response({'success': False, 'error': 'Failed to get upload SAS URL'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            result, blob_id = api_instance.blob_create(file_name, file_size_bytes, "file", uploaded)
            # add a debug log with format
            print(['DEBUG'], "BLOB CREATE : Blob Name : {}, Blob Size Bytes : {}, Blob Type : {}, blob_id : {}".format(file_name, file_size_bytes, "file", blob_id))
            if not result:
                return Response({'success': False, 'error': 'Blob creation failed'}, status=status.HTTP_400_BAD_REQUEST)
            
            # On success, return JSON for API clients
            if _is_api_request(request):
                return Response({'success': True, 'blob_id': blob_id}, status=status.HTTP_201_CREATED)
            # browser/form -> redirect to home
            return redirect('/home/')
        # If api_instance is None
        return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteBlobAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, blob_id=None):
        if not blob_id:
            return Response({'success': False, 'error': 'Missing blob ID'}, status=status.HTTP_400_BAD_REQUEST)

        print("DELETE : Blob ID :", blob_id, ":")
        user_info = None
        try:
            user_info = UserInfo.objects.get(user=request.user)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_container_instance(user_info.user_name)
        if api_instance:
            if not api_instance.blob_delete(blob_id):
                return Response({'success': False, 'error': 'Blob deletion failed'}, status=status.HTTP_400_BAD_REQUEST)
            # On success, return JSON for API clients
            if _is_api_request(request):
                return Response({'success': True}, status=status.HTTP_200_OK)
            # browser/form -> redirect to home
            return redirect('/home/')
        # If api_instance is None
        return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HomeAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        user = request.user
        # Redirect unauthenticated users to Login view
        if not request.user or not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)

        user_info_qs = UserInfo.objects.filter(user=user).values()
        if user_info_qs.count() != 1:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_container_instance(user_info_qs[0]['user_name'])
        if not api_instance:
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        blob_list = api_instance.get_blob_list()

        # convert numeric uploaded_at to datetime for the template
        for blob_obj in blob_list:
            ts = blob_obj.get('uploaded_at')
            try:
                blob_obj['uploaded_at_dt'] = datetime.fromtimestamp(float(ts)) if ts is not None else None
            except Exception:
                blob_obj['uploaded_at_dt'] = None

        # Decide whether to return JSON (API client) or render HTML (browser)
        if _is_api_request(request):
            return Response({'success': True, 'blobs': blob_list, 'username': user.username}, status=status.HTTP_200_OK)

        # render HTML for normal browser navigation
        context = {'success': True, 'blobs': blob_list, 'username': user.username}
        return render(request, 'main/sample.html', context)