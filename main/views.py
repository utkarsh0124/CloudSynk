from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect
from .serializers import UserSerializer, OTPVerifySerializer
from az_intf.api_utils import utils as app_utils
from az_intf import api as az_api
from .models import UserInfo, PendingUser
from django.contrib.auth.hashers import make_password
from storage_webapp.settings import DEFAULT_SUBSCRIPTION_AT_INIT
from .subscription_config import SUBSCRIPTION_CHOICES, SUBSCRIPTION_VALUES
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from django.conf import settings
from django.core.mail import send_mail  # keep for backward compatibility if needed
from .mailing import send_otp_email
from apiConfig import AZURE_API_DISABLE
from datetime import datetime, timedelta
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from storage_webapp import logger, severity
from django.http import StreamingHttpResponse
from .utils import get_avatar_url
import requests
import random

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
        # Stage user signup in SignupRequest
        code = f"{random.randint(100000, 999999)}"
        expires_at = timezone.now() + timedelta(minutes=10)
        # Create or update pending signup to avoid duplicates
        pending = PendingUser.objects.filter(username=username).first()
        if pending:
            if pending.is_expired():
                pending.delete()
                pending = PendingUser.objects.create(
                    username=username,
                    password=make_password(password),
                    email=email,
                    code=code,
                    expires_at=expires_at
                )
            else:
                pending.code = code
                pending.expires_at = expires_at
                pending.password = make_password(password)
                pending.email = email
                pending.save()
        else:
            pending = PendingUser.objects.create(
                username=username,
                password=make_password(password),
                email=email,
                code=code,
                expires_at=expires_at
            )
        # Send OTP via email
        subject = 'Your CloudSynk OTP Verification Code'
        message = f'Use the following OTP to verify your account: {code}'
        from_email = settings.DEFAULT_FROM_EMAIL
        # Send OTP via SMTP utility
        try:
            send_otp_email(email, subject, message)
        except Exception as e:
            logger.log(severity['ERROR'], f"Failed to send OTP email: {e}")
        # Return response indicating OTP sent (API) or render OTP page (browser)
        if _is_api_request(request):
            return Response({'success': True, 'message': 'OTP sent to email.', 'pending_id': pending.id}, status=status.HTTP_201_CREATED)
        return render(request, 'user/verify_otp.html', {'pending_id': pending.id})

class OTPVerifyAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        pending_id = request.data.get('pending_id')
        code = request.data.get('code')
        try:
            pending = PendingUser.objects.get(id=pending_id)
        except PendingUser.DoesNotExist:
            return Response({'success': False, 'error': 'Invalid request reference'}, status=status.HTTP_400_BAD_REQUEST)
        # Check max OTP entry attempts
        if pending.otp_attempts >= 5:
            pending.delete()
            return Response({'success': False, 'error': 'Maximum OTP attempts exceeded. Please signup again.'}, status=status.HTTP_403_FORBIDDEN)
        # Validate code
        if pending.code != code or pending.is_expired():
            pending.otp_attempts += 1
            pending.save()
            attempts_left = max(0, 5 - pending.otp_attempts)
            return Response(
                {
                    'success': False,
                    'error': 'Incorrect OTP. Please try again.',
                    'attempts_left': attempts_left
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        # Successful verification, proceed
        # Create actual user with hashed password
        user = User.objects.create(
            username=pending.username,
            password=pending.password,
            email=pending.email
        )
        user.is_active = True
        user.save()

        # Initialize container
        created = az_api.init_container(user, user.username, app_utils.assign_container(user.username), user.email)
        if not created:
            return Response({'success': False, 'error': 'Container initialization failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Remove pending registration
        pending.delete()
        return Response({'success': True, 'message': 'Account created and activated.'}, status=status.HTTP_200_OK)

class ResendOTPAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        pending_id = request.data.get('pending_id')
        if not pending_id:
            return Response({'success': False, 'error': 'Missing pending_id'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pending = PendingUser.objects.get(id=pending_id)
        except PendingUser.DoesNotExist:
            return Response({'success': False, 'error': 'Invalid request reference'}, status=status.HTTP_400_BAD_REQUEST)
        # Check expiration
        if pending.is_expired():
            pending.delete()
            return Response({'success': False, 'error': 'OTP request expired, please signup again.'}, status=status.HTTP_400_BAD_REQUEST)
        # Throttle resends
        now = timezone.now()
        elapsed = (now - pending.last_sent_at).total_seconds()
        if elapsed < 180:
            retry_after = int(180 - elapsed)
            return Response({'success': False, 'error': f'Please wait {retry_after}s before resending.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        if pending.resend_count >= 2:
            return Response({'success': False, 'error': 'Maximum resend attempts reached.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        # Generate new OTP
        code = f"{random.randint(100000, 999999)}"
        pending.code = code
        pending.last_sent_at = now
        pending.expires_at = now + timedelta(minutes=10)
        pending.resend_count += 1
        pending.save()
        # Send OTP via email
        subject = 'Your CloudSynk OTP Verification Code'
        message = f'Use the following OTP to verify your account: {code}'
        # Send OTP via SMTP utility
        try:
            send_otp_email(pending.email, subject, message)
        except Exception as e:
            logger.log(severity['ERROR'], f"Failed to resend OTP email: {e}")
        resends_left = max(0, 2 - pending.resend_count)
        return Response({'success': True, 'resend_count': pending.resend_count, 'resends_left': resends_left}, status=status.HTTP_200_OK)

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

        # Recalculate storage usage to ensure accuracy
        api_instance.recalculate_storage_usage()
        
        # Refresh user_info_obj after storage recalculation
        user_info_obj = UserInfo.objects.filter(user=user).values()[0]
        
        # Get the UserInfo model instance for avatar URL calculation
        user_info_instance = UserInfo.objects.get(user=user)
        avatar_url = get_avatar_url(user_info_instance)
        if avatar_url is None:
            logger.log(severity['ERROR'], f"Failed to get avatar URL for user {user.username}, using default placeholder")
        
        # Add avatar URL to the context object
        user_info_obj['avatar_url'] = avatar_url

        # Check if user is admin
        is_admin = is_admin_user(user)
        
        blob_list = []
        admin_users = []
        
        if is_admin:
            # For admin users, get user list instead of blob list
            all_users = User.objects.all().order_by('-date_joined')
            for usr in all_users:
                try:
                    usr_info = UserInfo.objects.get(user=usr)
                    admin_users.append({
                        'id': usr.id,
                        'username': usr.username,
                        'email': usr.email,
                        'is_active': usr.is_active,
                        'date_joined': usr.date_joined,
                        'last_login': usr.last_login,
                        'user_name': usr_info.user_name,
                        'subscription_type': usr_info.subscription_type,
                        'storage_used_bytes': usr_info.storage_used_bytes,
                        'storage_quota_bytes': usr_info.storage_quota_bytes,
                        'is_admin': usr.is_superuser or usr.is_staff or usr_info.subscription_type == 'OWNER',
                        'avatar_url': usr_info.avatar_url
                    })
                except UserInfo.DoesNotExist:
                    admin_users.append({
                        'id': usr.id,
                        'username': usr.username,
                        'email': usr.email,
                        'is_active': usr.is_active,
                        'date_joined': usr.date_joined,
                        'last_login': usr.last_login,
                        'user_name': usr.username,
                        'subscription_type': 'TESTER',
                        'storage_used_bytes': 0,
                        'storage_quota_bytes': SUBSCRIPTION_VALUES['TESTER'],
                        'is_admin': usr.is_superuser or usr.is_staff,
                        'avatar_url': None
                    })
        else:
            # For regular users, get blob list
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
                'admin_users': admin_users,
                'is_admin': is_admin,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_authenticated': True
                },
                'user_info': user_info_obj,
                'subscription_choices': [{'value': choice[0], 'label': choice[1]} for choice in SUBSCRIPTION_CHOICES]
            }, status=status.HTTP_200_OK)
        else:
            # For direct browser access, render the template
            context = {
                'success': True, 
                'user_info': user_info_obj,
                'blobs': blob_list,
                'admin_users': admin_users,
                'is_admin': is_admin,
                'user': user,  # Add user object for template consistency
                'subscription_choices': SUBSCRIPTION_CHOICES
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
        
        # Debug logging - log all request data
        logger.log(severity['DEBUG'], f"CHUNKED UPLOAD REQUEST: user={user.username}")
        logger.log(severity['DEBUG'], f"CHUNKED UPLOAD DATA: {list(request.data.keys())}")
        logger.log(severity['DEBUG'], f"CHUNKED UPLOAD FILES: {list(request.FILES.keys())}")
        
        # Log specific parameters
        upload_id = request.data.get('upload_id')
        chunk_index = request.data.get('chunk_index')
        total_chunks = request.data.get('total_chunks')
        file_name = request.data.get('file_name')
        total_size = request.data.get('total_size')
        chunk_data = request.FILES.get('chunk')
        
        logger.log(severity['DEBUG'], f"CHUNKED UPLOAD PARAMS: upload_id={upload_id}, chunk_index={chunk_index}, total_chunks={total_chunks}, file_name={file_name}, total_size={total_size}")
        logger.log(severity['DEBUG'], f"CHUNKED UPLOAD CHUNK: {chunk_data.name if chunk_data else None}, size={chunk_data.size if chunk_data else None}")
        
        try:
            user_info = UserInfo.objects.get(user=user)
            logger.log(severity['DEBUG'], f"CHUNKED UPLOAD: Found user_info for {user.username}")
        except UserInfo.DoesNotExist:
            logger.log(severity['ERROR'], f"CHUNKED UPLOAD: UserInfo not found for {user.username}")
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate required parameters
        if not upload_id:
            logger.log(severity['ERROR'], "CHUNKED UPLOAD: Missing upload_id")
            return Response({'success': False, 'error': 'Missing upload_id parameter'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file_name:
            logger.log(severity['ERROR'], "CHUNKED UPLOAD: Missing file_name")
            return Response({'success': False, 'error': 'Missing file_name parameter'}, status=status.HTTP_400_BAD_REQUEST)
            
        if not chunk_data:
            logger.log(severity['ERROR'], "CHUNKED UPLOAD: Missing chunk data")
            return Response({'success': False, 'error': 'Missing chunk data'}, status=status.HTTP_400_BAD_REQUEST)

        # Convert string parameters to integers
        try:
            chunk_index = int(chunk_index) if chunk_index is not None else 0
            total_chunks = int(total_chunks) if total_chunks is not None else 1
            total_size = int(total_size) if total_size is not None else 0
        except (ValueError, TypeError) as e:
            logger.log(severity['ERROR'], f"CHUNKED UPLOAD: Parameter conversion error: {e}")
            return Response({'success': False, 'error': f'Invalid parameter format: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        logger.log(severity['DEBUG'], f"CHUNKED UPLOAD: Converted params - chunk_index={chunk_index}, total_chunks={total_chunks}, total_size={total_size}")

        if not all([upload_id, file_name, chunk_data]):
            logger.log(severity['ERROR'], f"CHUNKED UPLOAD: Missing required parameters after validation")
            return Response({'success': False, 'error': 'Missing required parameters'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_container_instance(user_info.user_name)
        if not api_instance:
            logger.log(severity['ERROR'], f"CHUNKED UPLOAD: API instance creation failed for {user_info.user_name}")
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Validate quota for the first chunk only (to avoid multiple validations for the same file)
        if chunk_index == 0:
            logger.log(severity['DEBUG'], f"CHUNKED UPLOAD: First chunk, validating quota and blob name")
            # Validate against user's quota and file name uniqueness
            blob_validation = api_instance.validate_new_blob_addition(total_size, file_name)
            logger.log(severity['DEBUG'], f"CHUNKED UPLOAD: Blob validation result: {blob_validation}")
            if not blob_validation[0]:
                logger.log(severity['ERROR'], f"CHUNKED UPLOAD: Blob validation failed: {blob_validation[1]}")
                return Response({'success': False, 'error': blob_validation[1]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Initialize streaming upload session for first chunk
            logger.log(severity['DEBUG'], f"CHUNKED UPLOAD: Initializing streaming upload session")
            init_result = api_instance.initialize_streaming_upload(file_name, upload_id, total_size)
            logger.log(severity['DEBUG'], f"CHUNKED UPLOAD: Init result: {init_result}")
            if not init_result['success']:
                logger.log(severity['ERROR'], f"CHUNKED UPLOAD: Streaming upload init failed: {init_result['error']}")
                return Response({'success': False, 'error': init_result['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            logger.log(severity['DEBUG'], f"CHUNKED UPLOAD: Appending chunk {chunk_index}")
            # Stream chunk directly to Azure
            chunk_result = api_instance.append_chunk_to_blob(upload_id, chunk_data, chunk_index)
            logger.log(severity['DEBUG'], f"CHUNKED UPLOAD: Chunk append result: {chunk_result}")
            if not chunk_result['success']:
                logger.log(severity['ERROR'], f"CHUNKED UPLOAD: Chunk append failed: {chunk_result['error']}")
                return Response({'success': False, 'error': chunk_result['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Check if upload is complete
            if chunk_index == total_chunks - 1:
                logger.log(severity['DEBUG'], f"CHUNKED UPLOAD: Final chunk, finalizing upload")
                # Finalize streaming upload
                finalize_result = api_instance.finalize_streaming_upload(upload_id, file_name)
                logger.log(severity['DEBUG'], f"CHUNKED UPLOAD: Finalize result: {finalize_result}")
                if finalize_result['success']:
                    logger.log(severity['INFO'], f"CHUNKED UPLOAD: Upload completed successfully")
                    return Response({
                        'success': True, 
                        'completed': True,
                        'blob_id': finalize_result['blob_id'],
                        'uploaded_size': finalize_result['uploaded_size'],
                        'duration': finalize_result.get('duration', 0),
                        'message': 'Upload completed successfully'
                    }, status=status.HTTP_201_CREATED)
                else:
                    logger.log(severity['ERROR'], f"CHUNKED UPLOAD: Finalization failed: {finalize_result['error']}")
                    return Response({'success': False, 'error': finalize_result['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            logger.log(severity['DEBUG'], f"CHUNKED UPLOAD: Chunk {chunk_index} completed successfully")
            return Response({
                'success': True,
                'completed': False,
                'chunk_index': chunk_index,
                'uploaded_size': chunk_result.get('uploaded_size', 0),
                'message': f'Chunk {chunk_index + 1}/{total_chunks} streamed to Azure'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.log(severity['ERROR'], f"CHUNKED UPLOAD: Streaming upload error: {str(e)}")
            return Response({'success': False, 'error': f'Streaming upload error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    
    def delete(self, request):
        """Cancel upload session"""
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

        cancel_result = api_instance.cancel_streaming_upload(upload_id)
        if cancel_result['success']:
            return Response(cancel_result, status=status.HTTP_200_OK)
        else:
            return Response(cancel_result, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class CancelDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, blob_id=None):
        """Cancel download session (mainly for logging - actual cancellation is client-side)"""
        if not blob_id:
            return Response({'success': False, 'error': 'Missing blob ID'}, status=status.HTTP_400_BAD_REQUEST)

        download_session_id = request.data.get('download_session_id')
        
        try:
            user_info = UserInfo.objects.get(user=request.user)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_container_instance(user_info.user_name)
        if not api_instance:
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        cancel_result = api_instance.cancel_blob_download(blob_id, download_session_id)
        return Response(cancel_result, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class ActiveUploadsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get list of active upload sessions for the user"""
        try:
            user_info = UserInfo.objects.get(user=request.user)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, status=status.HTTP_400_BAD_REQUEST)

        api_instance = az_api.get_container_instance(user_info.user_name)
        if not api_instance:
            return Response({'success': False, 'error': 'API Instantiation Failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        active_sessions = api_instance.get_active_upload_sessions()
        return Response(active_sessions, status=status.HTTP_200_OK)


# Admin views for managing users
def is_admin_user(user):
    """Check if user has admin privileges"""
    try:
        user_info = UserInfo.objects.get(user=user)
        return (user.is_superuser or user.is_staff or 
                user_info.subscription_type == 'OWNER')
    except UserInfo.DoesNotExist:
        return user.is_superuser or user.is_staff

@method_decorator(csrf_exempt, name='dispatch')
class AdminUserListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get list of all users for admin interface"""
        # Check if requesting user is admin
        if not is_admin_user(request.user):
            if not _is_api_request(request):
                return redirect('home')
            return Response({'success': False, 'error': 'Insufficient permissions'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Get all users with their UserInfo
        users_data = []
        users = User.objects.all().order_by('-date_joined')
        
        for user in users:
            try:
                user_info = UserInfo.objects.get(user=user)
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_active': user.is_active,
                    'date_joined': user.date_joined,
                    'last_login': user.last_login,
                    'user_name': user_info.user_name,
                    'subscription_type': user_info.subscription_type,
                    'storage_used_bytes': user_info.storage_used_bytes,
                    'storage_quota_bytes': user_info.storage_quota_bytes,
                    'is_admin': user.is_superuser or user.is_staff or user_info.subscription_type == 'OWNER',
                    'avatar_url': user_info.avatar_url
                })
            except UserInfo.DoesNotExist:
                # User without UserInfo (shouldn't happen in normal cases)
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_active': user.is_active,
                    'date_joined': user.date_joined,
                    'last_login': user.last_login,
                    'user_name': user.username,
                    'subscription_type': 'TESTER',
                    'storage_used_bytes': 0,
                    'storage_quota_bytes': SUBSCRIPTION_VALUES['TESTER'],
                    'is_admin': user.is_superuser or user.is_staff,
                    'avatar_url': None
                })
        
        return Response({'success': True, 'users': users_data}, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch') 
class AdminDeleteUserAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        """Delete a user (admin only)"""
        # Check if requesting user is admin
        if not is_admin_user(request.user):
            return Response({'success': False, 'error': 'Insufficient permissions'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Get target user
            target_user = User.objects.get(id=user_id)
            
            # Prevent self-deletion
            if target_user.id == request.user.id:
                return Response({'success': False, 'error': 'Cannot delete your own account'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Get user info for logging and container deletion
            try:
                target_user_info = UserInfo.objects.get(user=target_user)
                username_for_log = target_user_info.user_name
                container_name = target_user_info.container_name
            except UserInfo.DoesNotExist:
                username_for_log = target_user.username
                container_name = None
            
            # Delete Azure storage container and all associated data
            if container_name and container_name != "None":
                try:
                    # Import Container class to handle Azure container deletion
                    from az_intf.api_utils.Container import Container
                    
                    # Create container instance for the target user
                    container_handler = Container(username_for_log)
                    
                    # Delete the Azure container and associated database records
                    container_deleted = container_handler.container_delete(target_user_info)
                    
                    if container_deleted:
                        logger.log(severity['INFO'], 
                                  f"Successfully deleted container '{container_name}' for user {username_for_log}")
                    else:
                        logger.log(severity['WARNING'], 
                                  f"Failed to delete container '{container_name}' for user {username_for_log}")
                        
                except Exception as container_error:
                    logger.log(severity['ERROR'], 
                              f"Error deleting container for user {username_for_log}: {str(container_error)}")
                    # Continue with user deletion even if container deletion fails
            
            # Delete the user (this will cascade delete UserInfo, Blob, Directory records due to CASCADE)
            target_user.delete()
            
            # Log the deletion
            logger.log(severity['INFO'], 
                      f"Admin {request.user.username} deleted user {username_for_log} (ID: {user_id}) and associated data")
            
            return Response({'success': True, 'message': 'User and all associated data deleted successfully'}, 
                          status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.log(severity['ERROR'], f"Error deleting user {user_id}: {str(e)}")
            return Response({'success': False, 'error': 'Failed to delete user'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class AdminUpdateUserSubscriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        """Update user subscription (admin only)"""
        # Check if requesting user is admin
        if not is_admin_user(request.user):
            return Response({'success': False, 'error': 'Insufficient permissions'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        subscription_type = request.data.get('subscription_type')
        
        # Validate subscription type
        valid_subscriptions = [choice[0] for choice in SUBSCRIPTION_CHOICES]
        if subscription_type not in valid_subscriptions:
            return Response({'success': False, 'error': 'Invalid subscription type'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get target user
            target_user = User.objects.get(id=user_id)
            target_user_info = UserInfo.objects.get(user=target_user)
            
            # Store old values for logging
            old_subscription = target_user_info.subscription_type
            old_quota = target_user_info.storage_quota_bytes
            
            # Update subscription
            target_user_info.subscription_type = subscription_type
            target_user_info.storage_quota_bytes = SUBSCRIPTION_VALUES[subscription_type]
            target_user_info.save()
            
            # Log the change
            logger.log(severity['INFO'], 
                      f"Admin {request.user.username} changed user {target_user_info.user_name} "
                      f"subscription from {old_subscription} to {subscription_type} "
                      f"(quota: {old_quota} -> {SUBSCRIPTION_VALUES[subscription_type]} bytes)")
            
            return Response({
                'success': True, 
                'message': 'Subscription updated successfully',
                'new_subscription': subscription_type,
                'new_quota_bytes': SUBSCRIPTION_VALUES[subscription_type]
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        except UserInfo.DoesNotExist:
            return Response({'success': False, 'error': 'User info not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.log(severity['ERROR'], 
                      f"Error updating subscription for user {user_id}: {str(e)}")
            return Response({'success': False, 'error': 'Failed to update subscription'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)