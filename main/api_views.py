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


class SignupAPIView(APIView):
    permission_classes = [permissions.AllowAny]

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
                return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'success': True, 'user_id': user.id}, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response({'success': False, 'error': 'Missing username or password'}, status=status.HTTP_400_BAD_REQUEST)

        if not app_utils.username_valid(username):
            return Response({'success': False, 'error': 'Invalid username'}, status=status.HTTP_400_BAD_REQUEST)

        if app_utils.user_exists(username):
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return Response({'success': True}, status=status.HTTP_200_OK)
            return Response({'success': False, 'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': False, 'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        az_api.del_api_instance()
        return Response({'success': True}, status=status.HTTP_200_OK)


class RemoveUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        usr_obj = request.user
        logout(request)

        try:
            user_info = UserInfo.objects.get(user=usr_obj)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_api_instance(usr_obj, user_info.container_name)
        if api_instance:
            api_instance.delete_container()
            az_api.del_api_instance()
            return Response({'success': True}, status=status.HTTP_200_OK)
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
            return Response({'success': True}, status=status.HTTP_200_OK)
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
            return Response({'success': True}, status=status.HTTP_200_OK)
        return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HomeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_info_qs = UserInfo.objects.filter(user=user).values()
        if user_info_qs.count() == 0:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_api_instance(user, user_info_qs[0]['container_name'])
        blob_list = api_instance.list_blob() if api_instance else []
        return Response({'success': True, 'blobs': blob_list, 'username': user.username}, status=status.HTTP_200_OK)
