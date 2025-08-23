from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect
from .serializers import UserSerializer
from . import utils as app_utils
from az_intf import api as az_api
from .models import UserInfo
from storage_webapp.settings import DEFAULT_SUBSCRIPTION_AT_INIT
from .subscription_config import SUBSCRIPTION_CHOICES, SUBSCRIPTION_VALUES


class SignupAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
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
