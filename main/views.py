import warnings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .subscription_config import SUBSCRIPTION_CHOICES, SUBSCRIPTION_VALUES
from storage_webapp.settings import DEFAULT_SUBSCRIPTION_AT_INIT
from az_intf import api
from .models import UserInfo
from az_intf import utils
from apiConfig import AZURE_API_DISABLE
from .serializers import SignupSerializer, LoginSerializer


class RemoveUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        usr_obj = request.user
        logout(request)
        try:
            user_info = UserInfo.objects.get(user=usr_obj)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = api.get_api_instance(request.user, user_info.container_name)
        if api_instance:
            api_instance.delete_container()
            api.del_api_instance()
            return Response({'success': True}, status=status.HTTP_200_OK)
        else:
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# This module contains DRF-style API endpoints and is the canonical API surface for the
# `main` app. Template/UI views were previously separate; those remain in templates if
# needed for the frontend, but API handlers live here.


# Deprecated: UI template view, not needed for DRF API


class SignupAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            # normalize serializer errors to {'error': message}
            errors = serializer.errors
            if 'non_field_errors' in errors:
                message = errors['non_field_errors'][0]
            else:
                # pick first field error
                first_key = next(iter(errors))
                message = errors[first_key][0]
            return Response({'success': False, 'error': str(message)}, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data['username']
        password1 = serializer.validated_data['password1']
        email = serializer.validated_data.get('email_id')

        if utils.user_exists(username):
            return Response({'success': False, 'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password1, email=email)
        user.save()
        user_info, created = UserInfo.objects.get_or_create(
            user=user,
            defaults = {
                'user_name': username,
                'subscription_type': dict(SUBSCRIPTION_CHOICES)[DEFAULT_SUBSCRIPTION_AT_INIT],
                'container_name': utils.assign_container(username),
                'storage_quota_bytes': dict(SUBSCRIPTION_VALUES)[DEFAULT_SUBSCRIPTION_AT_INIT],
                'storage_used_bytes': 0,
                'dob' : None,
                'email_id' : email
            }
        )
        if created:
            api_instance = api.get_api_instance(user, utils.assign_container(username))
            if api_instance:
                api_instance.add_container(user)
                return Response({'success': True, 'user_id': user.id}, status=status.HTTP_201_CREATED)
            else:
                user.delete()
                user_info.delete()
                return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({'success': False, 'error': 'User already exists'}, status=status.HTTP_400_BAD_REQUEST)



# Deprecated: UI template view, not needed for DRF API



class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            first_key = next(iter(errors))
            message = errors[first_key][0]
            return Response({'success': False, 'error': str(message)}, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        if not utils.username_valid(username):
            return Response({'success': False, 'error': 'Invalid username'}, status=status.HTTP_400_BAD_REQUEST)

        if utils.user_exists(username):
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                # create or get token for API clients
                token, _ = Token.objects.get_or_create(user=user)
                return Response({'success': True, 'token': token.key}, status=status.HTTP_200_OK)
            else:
                return Response({'success': False, 'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': False, 'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # remove session and revoke token for API clients
        logout(request)
        try:
            Token.objects.filter(user=request.user).delete()
        except Exception:
            # don't fail logout if token deletion has issues; proceed to cleanup
            pass
        api.del_api_instance()
        return Response({'success': True}, status=status.HTTP_200_OK)



class AddBlobAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_info = UserInfo.objects.get(user=request.user)
        file_name = request.data.get('file_name') or request.query_params.get('file_name')
        if not file_name:
            return Response({'success': False, 'error': 'Missing file name'}, status=status.HTTP_400_BAD_REQUEST)

        file_size_bytes = 100
        if user_info.storage_used_bytes + file_size_bytes >= user_info.storage_quota_bytes:
            return Response({'success': False, 'error': 'Storage Exceeded! Upload Failed'}, status=status.HTTP_400_BAD_REQUEST)

        user_info.storage_used_bytes += file_size_bytes
        user_info.save()

        api_instance = api.get_api_instance(request.user, user_info.container_name)
        if api_instance:
            api_instance.create_blob(file_name)
            return Response({'success': True}, status=status.HTTP_200_OK)
        else:
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class DeleteBlobAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, blob_name=None):
        user_info = UserInfo.objects.get(user=request.user)
        api_instance = api.get_api_instance(request.user, user_info.container_name)
        if api_instance:
            size = api_instance.get_blob_size(blob_name)
            user_info.storage_used_bytes = max(0, user_info.storage_used_bytes - size)
            user_info.save()
            api_instance.delete_blob(blob_name)
            return Response({'success': True}, status=status.HTTP_200_OK)
        else:
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class HomeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_info_qs = UserInfo.objects.filter(user=request.user).values()
        if user_info_qs.count() == 0:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = api.get_api_instance(request.user, user_info_qs[0]['container_name'])
        blob_list = api_instance.list_blob() if api_instance else []
        return Response({'success': True, 'blobs': blob_list, 'username': request.user.username}, status=status.HTTP_200_OK)