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
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from storage_webapp import logger, severity
from django.http import StreamingHttpResponse
import requests

def _is_api_request(request):
    """Return True if the request should be treated as an API/XHR call returning JSON.
    
    This helps distinguish between:
    - AJAX requests from our SPA (should get JSON responses)
    - Direct browser navigation (should get redirects/HTML)
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
        # Browser request: render signup template
        if not _is_api_request(request):
            return render(request, 'user/signup.html')
        # API request: return signup form structure
        return Response({
            'success': True,
            'form_fields': {
                'username': {'type': 'text', 'required': True},
                'email': {'type': 'email', 'required': True},
                'password1': {'type': 'password', 'required': True},
                'password2': {'type': 'password', 'required': True}
            }
        }, status=status.HTTP_200_OK)

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
        
        # API request: return JSON; browser request: redirect to login
        if _is_api_request(request):
            return Response({'success': True, 'user_id': user.id}, status=status.HTTP_201_CREATED)
        return redirect('/login/')

class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # If already logged in
        if request.user and request.user.is_authenticated:
            # For API requests, return user info JSON
            if _is_api_request(request):
                return Response({
                    'success': True, 
                    'already_authenticated': True,
                    'user': {
                        'id': request.user.id,
                        'username': request.user.username,
                        'email': request.user.email
                    }
                }, status=status.HTTP_200_OK)
            # For browser requests, redirect to home
            return redirect('/')
        
        # For API requests, return form structure for frontend rendering
        if _is_api_request(request):
            return Response({
                'success': True,
                'form_fields': {
                    'username': {'type': 'text', 'required': True},
                    'password': {'type': 'password', 'required': True}
                }
            }, status=status.HTTP_200_OK)
        
        # For browser requests, render the login template
        return render(request, 'user/login.html')

    def post(self, request):
        # Authenticate credentials from JSON or form data
        username = request.data.get('username') or request.POST.get('username')
        password = request.data.get('password') or request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # Browser form submission: redirect to home page
            if not _is_api_request(request):
                return redirect('/home/')
            # API request: return JSON success
            return Response({'success': True}, status=status.HTTP_200_OK)

        # Authentication failed
        if _is_api_request(request):
            return Response({'success': False, 'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        # Browser: re-render login with error message
        return render(request, 'user/login.html', {'error': 'Invalid username or password'})

@method_decorator(csrf_exempt, name='dispatch')
class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # For API requests, return logout confirmation
        if _is_api_request(request):
            if request.user and request.user.is_authenticated:
                return Response({
                    'success': True,
                    'message': 'Ready to logout',
                    'user': request.user.username
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'error': 'Not authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # For browser requests, perform logout and redirect
        if request.user and request.user.is_authenticated:
            logout(request)
            az_api.del_container_instance(request.user.username)
        return redirect('/login/')

    def post(self, request):
        logout(request)
        if not az_api.del_container_instance(request.user.username):
            return Response({'success': False, 'error': 'Error deleting container instance'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # For API requests, return JSON response
        if _is_api_request(request):
            return Response({'success': True}, status=status.HTTP_200_OK)
        
        # For browser requests, redirect to login
        return redirect('/login/')

class DeactivateUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        usr_obj = request.user
        api_instance = az_api.get_container_instance(usr_obj.username)
        if api_instance:
            try:
                # Delete container and all user data
                api_instance.container_delete(usr_obj)
                az_api.del_container_instance(usr_obj.username)
                
                # Delete the user
                usr_obj.delete()
                logout(request)
                
                # For API requests, return JSON response
                if _is_api_request(request):
                    return Response({'success': True, 'message': 'Account deactivated.'}, status=status.HTTP_200_OK)
                
                # For browser requests, redirect to login
                return redirect('/login/')
                
            except Exception as e:
                logger.log(severity['ERROR'], f"Deactivation error: {str(e)}")
                
                if _is_api_request(request):
                    return Response({'success': False, 'error': f'Deactivation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # For browser requests, redirect back with error message
                return redirect('/?error=deactivation_failed')
        
        # API instance failed
        if _is_api_request(request):
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return redirect('/?error=api_instantiation_failed')

@method_decorator(csrf_exempt, name='dispatch')
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
        
        # get file size in bytes
        file_size_bytes = blob_file.size
        if file_size_bytes <= 0:
            # handle error
            return Response({'success': False, 'error': 'Uploaded file is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        api_instance = az_api.get_container_instance(user_info.user_name)
        if api_instance:
            blob_validation = api_instance.validate_new_blob_addition(file_size_bytes, file_name)
            if not blob_validation[0]:
                return Response({'success': False, 'error': blob_validation[1]}, status=status.HTTP_400_BAD_REQUEST)

            result, blob_id = api_instance.blob_create(file_name, file_size_bytes, "file", blob_file)
            # add a debug log with format
            if result == False:
                return Response({'success': False, 'error': 'Blob creation failed'}, status=status.HTTP_400_BAD_REQUEST)

            # Always return JSON response
            return Response({'success': True, 'blob_id': blob_id}, status=status.HTTP_201_CREATED)
        # If api_instance is None
        return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class DeleteBlobAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, blob_id=None):
        if not blob_id:
            return Response({'success': False, 'error': 'Missing blob ID'}, status=status.HTTP_400_BAD_REQUEST)

        user_info = None
        try:
            user_info = UserInfo.objects.get(user=request.user)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_container_instance(user_info.user_name)
        if api_instance:
            if not api_instance.blob_delete(blob_id):
                return Response({'success': False, 'error': 'Blob deletion failed'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Always return JSON response
            return Response({'success': True}, status=status.HTTP_200_OK)
        # If api_instance is None
        return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HomeAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        user = request.user
        # Handle unauthenticated users
        if not request.user or not request.user.is_authenticated:
            # For API requests, return JSON error
            if _is_api_request(request):
                return Response({'success': False, 'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            # For browser requests, redirect to login
            return redirect(settings.LOGIN_URL)

        user_info_obj = UserInfo.objects.filter(user=user).values()
        if user_info_obj.count() != 1:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)
        user_info_obj = user_info_obj[0]
        api_instance = az_api.get_container_instance(user_info_obj['user_name'])
        if not api_instance:
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        blob_list = api_instance.get_blob_info()

        # convert numeric uploaded_at to datetime string for JSON serialization
        for blob_obj in blob_list:
            ts = blob_obj['blob_uploaded_at']
            try:
                if ts is not None:
                    dt = datetime.fromtimestamp(float(ts))
                    blob_obj['blob_uploaded_at_formatted'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    blob_obj['blob_uploaded_at_formatted'] = None
            except Exception:
                blob_obj['blob_uploaded_at_formatted'] = None

        if _is_api_request(request):
            return Response({
                'success': True, 
                'blobs': blob_list, 
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_authenticated': True
                },
                'user_info': user_info_obj
            }, status=status.HTTP_200_OK)
        else:
            # For direct browser access, render the template
            context = {
                'success': True, 
                'user_info': user_info_obj,
                'blobs': blob_list
            }
            return render(request, 'main/sample.html', context)

@method_decorator(csrf_exempt, name='dispatch')
class DownloadBlobAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, blob_id=None):
        if not blob_id:
            return Response({'success': False, 'error': 'Missing blob ID'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_info = UserInfo.objects.get(user=request.user)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_container_instance(user_info.user_name)
        if not api_instance:
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Get blob info to verify ownership and get blob name
        try:
            blob_info = api_instance.get_blob_info(blob_id)
            if not blob_info:
                return Response({'success': False, 'error': 'Blob not found'}, status=status.HTTP_404_NOT_FOUND)
            blob_info = blob_info[0]  # get the first item from the list
        except Exception as e:
            return Response({'success': False, 'error': f'Error retrieving blob info: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Parse Range header for resume support
        range_header = request.META.get('HTTP_RANGE')
        # get blob_size from list of blobs
        file_size = blob_info['blob_size']
        start = 0
        end = file_size - 1

        if range_header:
            # Chunk based Downloading
            # Parse "bytes=start-end" format
            try:
                range_match = range_header.replace('bytes=', '').split('-')
                if range_match[0]:
                    start = int(range_match[0])
                if range_match[1]:
                    end = int(range_match[1])
            except (ValueError, IndexError):
                return Response({'success': False, 'error': 'Invalid range header'}, status=status.HTTP_400_BAD_REQUEST)

        # Stream the file through Django using direct service client with range support
        try:
            # Get blob stream with range support if specified
            if range_header:
                blob_stream = api_instance.get_blob_stream_range(blob_id, start, end)
            else:
                blob_stream = api_instance.get_blob_stream(blob_id)
                
            if not blob_stream:
                return Response({'success': False, 'error': 'Failed to get blob stream'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Stream the file from Azure through our server
            def file_generator():
                try:
                    for chunk in blob_stream.chunks():
                        yield chunk
                except Exception as e:
                    logger.log(severity['ERROR'], f"Error streaming file: {str(e)}")
                    raise

            response = StreamingHttpResponse(
                file_generator(),
                content_type='application/octet-stream'
            )
            
            # Set headers for resumable download
            filename = blob_info['blob_name']
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Accept-Ranges'] = 'bytes'
            
            # Set partial content status if range request
            if range_header:
                response.status_code = 206  # Partial Content
                response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                response['Content-Length'] = str(end - start + 1)
            else:
                response['Content-Length'] = str(file_size)
            
            return response
            
        except Exception as e:
            return Response({'success': False, 'error': f'Error downloading file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class ChunkedUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Handle chunked file upload with resume support"""
        user = request.user
        
        try:
            user_info = UserInfo.objects.get(user=user)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        # Get upload parameters
        upload_id = request.data.get('upload_id')
        chunk_index = int(request.data.get('chunk_index', 0))
        total_chunks = int(request.data.get('total_chunks', 1))
        file_name = request.data.get('file_name')
        total_size = int(request.data.get('total_size', 0))
        chunk_data = request.FILES.get('chunk')

        if not all([upload_id, file_name, chunk_data]):
            return Response({'success': False, 'error': 'Missing required parameters'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_container_instance(user_info.user_name)
        if not api_instance:
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Validate quota for the first chunk only (to avoid multiple validations for the same file)
        if chunk_index == 0:
            # Validate against user's quota and file name uniqueness
            blob_validation = api_instance.validate_new_blob_addition(total_size, file_name)
            if not blob_validation[0]:
                return Response({'success': False, 'error': blob_validation[1]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Store chunk
            result = api_instance.store_upload_chunk(
                upload_id=upload_id,
                chunk_index=chunk_index,
                chunk_data=chunk_data,
                file_name=file_name,
                total_chunks=total_chunks,
                total_size=total_size
            )
            
            if not result:
                return Response({'success': False, 'error': 'Failed to store chunk'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Check if upload is complete
            if chunk_index == total_chunks - 1:
                # Finalize upload synchronously but with progress updates
                blob_id = api_instance.finalize_chunked_upload(upload_id, file_name, total_size)
                if blob_id:
                    return Response({
                        'success': True, 
                        'completed': True,
                        'blob_id': blob_id,
                        'message': 'Upload completed'
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({'success': False, 'error': 'Failed to finalize upload'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'success': True,
                'completed': False,
                'chunk_index': chunk_index,
                'message': f'Chunk {chunk_index + 1}/{total_chunks} uploaded'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'success': False, 'error': f'Upload error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """Get upload status for resume"""
        upload_id = request.query_params.get('upload_id')
        if not upload_id:
            return Response({'success': False, 'error': 'Missing upload_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_info = UserInfo.objects.get(user=request.user)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_container_instance(user_info.user_name)
        if not api_instance:
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        upload_status = api_instance.get_upload_status(upload_id)
        return Response({'success': True, 'upload_status': upload_status}, status=status.HTTP_200_OK)