import time
import base64
import re

# from django.contrib.auth.models import User
from azure.storage.blob import ContainerClient, BlobServiceClient
from main.models import UserInfo, Blob
from az_intf.api_utils import utils as app_utils
from main.subscription_config import SUBSCRIPTION_CHOICES, SUBSCRIPTION_VALUES
from storage_webapp import logger, severity
from storage_webapp.settings import DEFAULT_SUBSCRIPTION_AT_INIT
from .utils import AZURE_STORAGE_ACCOUNT_NAME, AZURE_STORAGE_ACCOUNT_KEY, AZURE_STORAGE_ENDPOINT_SUFFIX
from .utils import validate_azure_blob_name, sanitize_azure_blob_name
from main.utils import generate_and_store_avatar


class Container:
    def __init__(self, username:str):
        self.__user_name = username
        self.__user_obj = UserInfo.objects.get(user_name=username)
        self.__service_client = BlobServiceClient(
                                    account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
                                    credential=AZURE_STORAGE_ACCOUNT_KEY
                                )
        self.__container_client = None
        if self.__user_obj.container_name is None or self.__user_obj.container_name=="":
            logger.log(severity['ERROR'], "CONTAINER DOES NOT EXIST")
            logger.log(severity['ERROR'], "FAILED TO INITIALIZE CONTAINER CLIENT")
            # Object not created
            assert False
        # Ensure container name is lowercase (Azure requirement)
        container_name_lower = self.__user_obj.container_name.lower()
        self.__container_client = self.__service_client.get_container_client(container_name_lower)

        # dictionary of key=blob name, value=blob object
        self.__blob_obj_dict = {blob_obj.blob_id: blob_obj for blob_obj in Blob.objects.filter(user_id=self.__user_obj.user_id)}
        
        # Track ongoing streaming uploads - Phase 1 optimization
        self.__active_uploads = {}
        
        # add debug log 
        logger.log(severity['DEBUG'], "CONTAINER INIT : User Name : {}, Container Name : {}, Blob Count : {}".format(username, self.__user_obj.container_name, len(self.__blob_obj_dict)))

    @staticmethod
    def user_exists(username:str):
        return UserInfo.objects.filter(user_name=username).exists()

    @classmethod
    def container_create(cls, 
                         user_obj,
                         username:str, 
                         container_name:str, 
                         # make sure this is Models.EmailField type
                         email_id):
        create_success=False
        ''' 
        AZURE API call to create a container for a user
        '''
        #---------------------------------------------------------------------------
        account_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.{AZURE_STORAGE_ENDPOINT_SUFFIX}"
        try:
            logger.log(severity['INFO'], f"Calling API to create Container '{container_name}'")
            service_client = BlobServiceClient(account_url=account_url, credential=AZURE_STORAGE_ACCOUNT_KEY)
            container_client = service_client.get_container_client(container_name)
            container_client.create_container()
            logger.log(severity['INFO'], f"Container '{container_name}' created.")
        #---------------------------------------------------------------------------
        except Exception as error:
            logger.log(severity['ERROR'], "CONTAINER CREATE EXCEPTION : {}".format(error))
            return create_success
        try:
            logger.log(severity['DEBUG'], "CONTAINER CREATE : User Name : {}, Container Name : {}, Email ID : {}".format(username, container_name, email_id))
            if UserInfo.objects.filter(container_name=container_name).exists():
                logger.log(severity['INFO'], "CONTAINER ALREADY EXISTS")
                return True
            logger.log(severity['DEBUG'], "CONTAINER CREATE SUCCESS : User Name : {}, Container Name : {}, Email ID : {}".format(username, container_name, email_id))
            
            # Generate and store avatar
            avatar_url = generate_and_store_avatar(username)
            if avatar_url is None:
                logger.log(severity['ERROR'], f"Failed to generate/store avatar for user {username}, using default placeholder")
            
            # add container to db
            user_info, created = UserInfo.objects.get_or_create(
                user=user_obj,
                defaults={
                    'user_name': username,
                    'subscription_type': dict(SUBSCRIPTION_CHOICES)[DEFAULT_SUBSCRIPTION_AT_INIT],
                    'container_name': container_name,
                    'storage_quota_bytes': dict(SUBSCRIPTION_VALUES)[DEFAULT_SUBSCRIPTION_AT_INIT],
                    'storage_used_bytes': 0,
                    'dob': None,
                    'email_id': email_id,
                    'avatar_url': avatar_url
                }
            )
            if not created:
                logger.log(severity['INFO'], "USER INFO ALREADY EXISTS")
                return True
            user_info.save()
            logger.log(severity['DEBUG'], "CONTAINER CREATE : User Name : {}, Container Name : {}, Email ID : {}".format(username, container_name, email_id))
             
            create_success = True
        except Exception as error:
            logger.log(severity['ERROR'], "SAMPLE CONTAINER CREATE EXCEPTION : {}".format(error))
        return create_success
    
    def __blob_id_exists(self, blob_id:str):
        logger.log(severity['DEBUG'], "BLOB ID EXISTS CHECK : Blob ID : {}".format(blob_id))
        return blob_id in self.__blob_obj_dict.keys()

    def __blob_name_exists(self, blob_name:str):
        logger.log(severity['DEBUG'], "BLOB NAME EXISTS CHECK : Blob Name : {}".format(blob_name))
        return blob_name in Blob.objects.filter(user_id=self.__user_obj.user).values_list('blob_name', flat=True)

    def __add_blob_to_db(self, blob_name:str, blob_size:int, blob_type:str="file"):
        logger.log(severity['DEBUG'], "BLOB CREATE : Blob Name : {}, Blob Size Bytes : {}, Blob Type : {}".format(blob_name, blob_size, blob_type))
        add_success = False
        assigned_blob_id = None
        try:
            if self.__blob_name_exists(blob_name):
                logger.log(severity['INFO'], "BLOB ALREADY EXISTS")
            else:
                blob_obj = Blob(
                    blob_name=blob_name,
                    blob_size=blob_size,
                    user_id=self.__user_obj.user,
                    creation_time=time.time(),
                    last_modification_time=time.time(),
                    blob_type=blob_type,
                    sharing_enabled=False,
                    is_in_directory=False,
                    directory_id=None
                )
                blob_obj.save()
                assigned_blob_id = blob_obj.blob_id
                self.__blob_obj_dict[assigned_blob_id] = blob_obj
                add_success = True
        except Exception as error:
            logger.log(severity['ERROR'], "BLOB ADD EXCEPTION : {}".format(error))
            add_success = False
        return (add_success, assigned_blob_id)

    def __delete_blob_from_db(self, blob_id):
        delete_success = False
        try:
            if not self.__blob_id_exists(blob_id):
                logger.log(severity['INFO'], "BLOB DOES NOT EXIST")
            else:
                Blob.objects.filter(blob_id=blob_id, user_id=self.__user_obj.user).delete()
                del self.__blob_obj_dict[blob_id]
                delete_success = True
        except Exception as error:
            logger.log(severity['ERROR'], "BLOB DELETE EXCEPTION : {}".format(error))
            delete_success = False
        return delete_success

    def __delete_container_from_db(self):
        delete_success = False
        try:
            Blob.objects.filter(user_id=self.__user_obj.user).delete()
            self.__blob_obj_dict.clear()
            UserInfo.objects.filter(user_name=self.__user_name).delete()
            delete_success = True
        except Exception as error:
            logger.log(severity['ERROR'], "BLOB DELETE ALL EXCEPTION : {}".format(error))
            delete_success = False
        return delete_success

    def validate_blob_name(self, blob_name: str) -> dict:
        """
        Validate blob name against Azure Storage naming requirements
        Auto-sanitizes invalid characters instead of rejecting them
        
        Returns:
            dict: {
                'is_valid': bool,
                'sanitized_name': str,
                'errors': list
            }
        """
        validation_result = validate_azure_blob_name(blob_name)
        
        # Instead of failing on invalid characters, auto-sanitize and allow upload
        if not validation_result['is_valid'] and validation_result['sanitized_name']:
            logger.log(severity['INFO'], f"AUTO-SANITIZED blob name: '{blob_name}' -> '{validation_result['sanitized_name']}'")
            # Return as valid since we have a sanitized version
            return {
                'is_valid': True,
                'sanitized_name': validation_result['sanitized_name'],
                'errors': []
            }
        
        return validation_result

    def validate_new_blob_addition(self, new_blob_size, blob_name):
        # First validate Azure blob naming requirements
        name_validation = self.validate_blob_name(blob_name)
        if not name_validation['is_valid']:
            error_msg = f"Invalid blob name: {'; '.join(name_validation['errors'])}"
            logger.log(severity['DEBUG'], f"BLOB NAME VALIDATION FAILED : {error_msg}")
            return (False, error_msg)
        
        # Use sanitized name for further checks
        sanitized_name = name_validation['sanitized_name']
        
        # validate against user's quota
        if self.__user_obj.storage_used_bytes + new_blob_size > self.__user_obj.storage_quota_bytes:
            logger.log(severity['DEBUG'], "BLOB VALIDATION FAILED : User Name : {}, Used : {}, Quota : {}, New Blob Size : {}".format(self.__user_name,
                       self.__user_obj.storage_used_bytes,
                       self.__user_obj.storage_quota_bytes,
                       new_blob_size))
            return (False, "Storage quota exceeded. Please delete some files before uploading new ones or Upgrade your Subscription")
        
        # validate blob name uniqueness (using sanitized name)
        if self.__blob_name_exists(sanitized_name):
            logger.log(severity['DEBUG'], "BLOB VALIDATION FAILED : Blob Name Already Exists : {}".format(sanitized_name))
            return (False, "Blob name already exists. Please use a different file.")

        return (True, "Success") 

    def recalculate_storage_usage(self):
        """Recalculate and update storage usage based on actual blob sizes in database"""
        try:
            from main.models import Blob
            from django.db.models import Sum
            # Calculate total size of all blobs for this user
            total_size = Blob.objects.filter(user_id=self.__user_obj.user).aggregate(
                total=Sum('blob_size')
            )['total'] or 0
            
            # Update the user's storage usage
            old_usage = self.__user_obj.storage_used_bytes
            self.__user_obj.storage_used_bytes = total_size
            self.__user_obj.save()
            
            logger.log(severity['INFO'], "STORAGE RECALCULATED : User : {}, Old : {}, New : {}".format(
                self.__user_name, old_usage, total_size))
            
            return True
        except Exception as error:
            logger.log(severity['ERROR'], "STORAGE RECALCULATION FAILED : {}".format(error))
            return False

    def get_blob_info(self, blob_id=None):
        try:
            if blob_id:
                # get specific blob in a list if blob_id provided
                queryset = Blob.objects.filter(user_id=self.__user_obj.user_id, blob_id=blob_id)
            else :
                # use filter to get all blobs for this user; self.__user_obj.user_id is the User PK
                queryset = Blob.objects.filter(user_id=self.__user_obj.user_id)
        except Exception as e:
            # unexpected errors (DB issues, etc.)
            logger.log(severity['ERROR'], "GET BLOB LIST EXCEPTION : {}".format(e))            
            return []
        return [
            {
                'blob_id' : b.blob_id,
                'blob_name': b.blob_name,
                'blob_size': b.blob_size,
                'blob_uploaded_at': b.creation_time,
                'blob_uploaded_at_formatted': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(b.creation_time)) if b.creation_time else None
                # 'blob_download_url': f'/download/{b.blob_name}'  # adjust as needed
            }
            for b in queryset
        ]

    def get_upload_status(self, upload_id):
        """Get status of chunked upload for resume"""
        try:
            if self.__container_client is None:
                logger.log(severity['ERROR'], "CONTAINER CLIENT NOT INITIALIZED")
                return None
                
            chunk_prefix = "temp_uploads/{}/chunk_".format(upload_id)
            chunks = []
            
            for blob in self.__container_client.list_blobs(name_starts_with=chunk_prefix):
                chunk_index = int(blob.metadata.get('chunk_index', 0))
                chunks.append({
                    'index': chunk_index,
                    'size': blob.size,
                    'timestamp': blob.metadata.get('timestamp')
                })
            
            # Sort by index
            chunks.sort(key=lambda x: x['index'])
            
            logger.log(severity['DEBUG'], "UPLOAD STATUS : Upload ID : {}, Chunks : {}".format(upload_id, len(chunks)))
            return {
                'upload_id': upload_id,
                'chunks_uploaded': len(chunks),
                'chunks': chunks
            }
            
        except Exception as error:
            logger.log(severity['ERROR'], "GET UPLOAD STATUS EXCEPTION : {}".format(error))
            return None

    # def blob_create(self,blob_name:str, blob_size_bytes:int, blob_type:str="file", blob_file=None):
    #     # add debug log using format print
    #     logger.log(severity['DEBUG'], "BLOB CREATE : Blob Name : {}, Blob Size Bytes : {}, Blob Type : {}".format(blob_name, blob_size_bytes, blob_type))
    #     assigned_blob_id = None
    #     try:
    #         # Validate Azure blob naming requirements
    #         name_validation = self.validate_blob_name(blob_name)
    #         if not name_validation['is_valid']:
    #             error_msg = f"Invalid blob name: {'; '.join(name_validation['errors'])}"
    #             logger.log(severity['WARNING'], f"BLOB NAME VALIDATION FAILED : {error_msg}")
    #             return (False, assigned_blob_id)
            
    #         # Use sanitized name
    #         sanitized_blob_name = name_validation['sanitized_name']
            
    #         if self.__blob_name_exists(sanitized_blob_name):
    #             logger.log(severity['INFO'], "BLOB ALREADY EXISTS")
    #             return (False, assigned_blob_id)
    #         # add debug log
    #         logger.log(severity['DEBUG'], "BLOB CREATE : Checking quota for user : {}, Used : {}, Quota : {}".format(self.__user_name,
    #                    self.__user_obj.storage_used_bytes,
    #                    self.__user_obj.storage_quota_bytes))

    #         # check against the user's quota
    #         if self.__user_obj.storage_used_bytes + blob_size_bytes >= self.__user_obj.storage_quota_bytes:
    #             logger.log(severity['INFO'], "STORAGE EXCEEDED")
    #             return (False, assigned_blob_id)

    #         # add debug log with format print
    #         logger.log(severity['DEBUG'], "BLOB CREATE : Quota OK for user : {}, Used : {}, Quota : {}".format(self.__user_name,
    #                    self.__user_obj.storage_used_bytes,
    #                    self.__user_obj.storage_quota_bytes))
            
    #         # update and save user's storage usage
    #         self.__user_obj.storage_used_bytes += blob_size_bytes
    #         self.__user_obj.save()

    #         # server side AZURE API call to create a blob for a user 
    #         #---------------------------------------------------------------------------
    #         if self.__container_client is not None:
    #             if not blob_file:
    #                 logger.log(severity['INFO'], "BLOB CREATE : No file provided, creating empty blob")
    #                 self.__user_obj.delete()
    #                 return (False, None)
    #             else:
    #                 logger.log(severity['INFO'], "BLOB CREATE : Uploading provided file as blob : {}".format(sanitized_blob_name))
    #                 blob_client = self.__container_client.get_blob_client(sanitized_blob_name)

    #                 file_like = getattr(blob_file, "file", blob_file)
    #                 blob_client.upload_blob(file_like, overwrite=True)
    #             logger.log(severity['INFO'], "BLOB CREATE : Blob '{}' created in container '{}'.".format(sanitized_blob_name, self.__user_obj.container_name))
    #         else:
    #             logger.log(severity['ERROR'], "BLOB CREATE FAILED : CONTAINER CLIENT NOT INITIALIZED")
    #             self.__user_obj.delete()
    #             return (False, assigned_blob_id)
    #         #---------------------------------------------------------------------------

    #         #add debug log
    #         logger.log(severity['DEBUG'], "BLOB CREATE : Updated storage used for user : {}, New Used : {}".format(self.__user_name,
    #                    self.__user_obj.storage_used_bytes))

    #         result, assigned_blob_id = self.__add_blob_to_db(sanitized_blob_name, blob_size_bytes, blob_type)
    #         if not result:
    #             logger.log(severity['ERROR'], "BLOB CREATE EXCEPTION")
    #             self.__user_obj.delete()
    #             return (False, assigned_blob_id)
    #     except Exception as error:
    #         logger.log(severity['ERROR'], "BLOB CREATE EXCEPTION : {}".format(error))
    #         return (False, assigned_blob_id)
    #     return (True, assigned_blob_id)

    def blob_delete(self, blob_id):
        try:
            if not self.__blob_id_exists(blob_id):
                logger.log(severity['INFO'], "BLOB DOES NOT EXIST")
                return False
            blob_name = self.__blob_obj_dict[blob_id].blob_name

            '''
            AZURE API call to delete a blob for a user
            '''
            #---------------------------------------------------------------------------
            if self.__container_client is None:
                logger.log(severity['INFO'], "CONTAINER CLIENT NOT INITIALIZED")
                return False
            
            #debug log
            logger.log(severity['DEBUG'], "BLOB DELETE : Deleting blob ID : {}, Blob Name : {}".format(blob_id, blob_name))
            blob_client = self.__container_client.get_blob_client(blob_name)
            delete_resp = blob_client.delete_blob()
            
            if delete_resp is None:
                if blob_client.exists():
                    logger.log(severity['ERROR'], "BLOB DELETE FAILED : Blob still exists after delete attempt")
                    return False
            elif delete_resp.status_code != 202:
                logger.log(severity['ERROR'], "BLOB DELETE FAILED WITH STATUS CODE : {}".format(delete_resp.status_code))
                return False
            
            logger.log(severity['INFO'], "BLOB DELETE : Blob ID : {}".format(blob_id))
            #---------------------------------------------------------------------------

            blob_info = self.get_blob_info(blob_id)
            if not blob_info:
                logger.log(severity['ERROR'], "BLOB INFO RETRIEVAL FAILED DURING DELETE")
                return False
            blob_info = blob_info[0]  # get the first item from the list
            # update and save this user's storage usage
            self.__user_obj.storage_used_bytes = max(0, self.__user_obj.storage_used_bytes - blob_info['blob_size'])
            self.__user_obj.save()

            if not self.__delete_blob_from_db(blob_id):
                logger.log(severity['ERROR'], "BLOB DELETE EXCEPTION")
                return False
        except Exception as error:
            logger.log(severity['ERROR'], "BLOB DELETE EXCEPTION : {}".format(error))
            return False
        return True
        
    def container_delete(self, user_obj):
        delete_success=False
        container_name = self.__user_obj.container_name
        if container_name is None or container_name=="":
            logger.log(severity['INFO'], "CONTAINER DOES NOT EXIST")
            return True
        try:
            ''' 
            AZURE API call to delete a container for a user
            '''
            #---------------------------------------------------------------------------
            self.__service_client.delete_container(container_name)
            logger.log(severity['INFO'], f"Container '{container_name}' deleted.")
            #---------------------------------------------------------------------------
            if not self.__delete_container_from_db():
                logger.log(severity['ERROR'], "SAMPLE CONTAINER DELETE EXCEPTION")
            else:
                delete_success=True
        except Exception as error:
            logger.log(severity['ERROR'], "SAMPLE CONTAINER DELETE ALL EXCEPTION : {}".format(error))
        return delete_success

    # =============================================================================
    # PHASE 1: STREAMING UPLOAD METHODS
    # =============================================================================

    def initialize_streaming_upload(self, file_name, upload_id, total_size):
        """Initialize a streaming upload session for direct-to-Azure chunk uploading"""
        try:
            logger.log(severity['DEBUG'], f"STREAMING UPLOAD INIT: file_name={file_name}, upload_id={upload_id}, total_size={total_size}")
            
            # Check for existing session
            if upload_id in self.__active_uploads:
                logger.log(severity['WARNING'], f"Upload session {upload_id} already exists")
                return {'success': False, 'error': 'Upload session already exists'}
            
            # Validate Azure blob naming requirements
            name_validation = self.validate_blob_name(file_name)
            if not name_validation['is_valid']:
                error_msg = f"Invalid file name: {'; '.join(name_validation['errors'])}"
                logger.log(severity['WARNING'], f"BLOB NAME VALIDATION FAILED : {error_msg}")
                return {'success': False, 'error': error_msg}
            
            # Use sanitized name
            blob_name = name_validation['sanitized_name']
            
            # Log if file name was changed during sanitization
            if blob_name != file_name:
                logger.log(severity['INFO'], f"File name sanitized: '{file_name}' -> '{blob_name}'")
                file_name=blob_name
            else:
                logger.log(severity['DEBUG'], f"Using blob name: {blob_name}")
            
            # Ensure container name is lowercase (Azure requirement)
            container_name = self.__user_obj.container_name.lower()
            
            # Create blob client for Azure operations
            blob_client = self.__service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            # Initialize upload session tracking
            self.__active_uploads[upload_id] = {
                'blob_client': blob_client,
                'blob_name': blob_name,
                'file_name': file_name,
                'total_size': total_size,
                'uploaded_blocks': [],
                'uploaded_size': 0,
                'start_time': time.time()
            }
            
            logger.log(severity['INFO'], f"STREAMING UPLOAD: Initialized session Upload ID:{upload_id} for BlobName:{blob_name}")
            return {'success': True, 'blob_name': blob_name}
            
        except Exception as e:
            logger.log(severity['ERROR'], f"Failed to initialize upload session {upload_id}: {str(e)}")
            return {'success': False, 'error': 'Failed to initialize upload session'}

    def append_chunk_to_blob(self, upload_id, chunk_data, chunk_index):
        """Stream a chunk directly to Azure blob storage using stage_block"""
        try:
            if upload_id not in self.__active_uploads:
                logger.log(severity['ERROR'], f"Upload session {upload_id} not found")
                return {'success': False, 'error': 'Upload session not found'}
            
            upload_session = self.__active_uploads[upload_id]
            blob_client = upload_session['blob_client']
            
            # Generate block ID (must be base64 encoded and same length for all blocks)
            block_id = base64.b64encode(f"block-{chunk_index:08d}".encode()).decode()
            
            # Read chunk data
            chunk_bytes = chunk_data.read()
            chunk_size = len(chunk_bytes)
            
            logger.log(severity['DEBUG'], f"STREAMING UPLOAD: Staging block {block_id} for {upload_id}, size={chunk_size}")
            
            print("Container:", blob_client.container_name)
            print("Blob:", blob_client.blob_name)
            print("URL:", blob_client.url)

            # Stage block directly to Azure
            blob_client.stage_block(
                block_id=block_id,
                data=chunk_bytes
            )
            logger.log(severity['DEBUG'], f"Staged block {block_id} for {upload_id}, size={chunk_size}")
            
            # Track the staged block
            upload_session['uploaded_blocks'].append(block_id)
            upload_session['uploaded_size'] += chunk_size
            
            logger.log(severity['DEBUG'], f"STREAMING UPLOAD: Successfully staged chunk {chunk_index} for {upload_id}")
            return {'success': True, 'uploaded_size': upload_session['uploaded_size']}
            
        except Exception as e:
            logger.log(severity['ERROR'], f"Failed to append chunk {chunk_index} for upload {upload_id}: {str(e)}")
            return {'success': False, 'error': f'Failed to upload chunk {chunk_index}'}

    def finalize_streaming_upload(self, upload_id, file_name):
        """Finalize the streaming upload by committing all staged blocks and creating DB record"""
        try:
            if upload_id not in self.__active_uploads:
                logger.log(severity['ERROR'], f"Upload session {upload_id} not found")
                return {'success': False, 'error': 'Upload session not found'}
            
            upload_session = self.__active_uploads[upload_id]
            blob_client = upload_session['blob_client']
            blob_name = upload_session['blob_name']
            total_uploaded = upload_session['uploaded_size']
            uploaded_blocks = upload_session['uploaded_blocks']
            start_time = upload_session['start_time']
            
            logger.log(severity['DEBUG'], f"STREAMING UPLOAD: Finalizing {upload_id}, committing {len(uploaded_blocks)} blocks")
            
            # Commit all staged blocks to create the final blob
            blob_client.commit_block_list(uploaded_blocks)
            
            # Create database record for the blob
            assigned_blob_id = self.__add_blob_to_db(blob_name, total_uploaded, "file")
            if not assigned_blob_id:
                raise Exception("Failed to create database record for uploaded file")
            
            # Update user storage usage
            self.__user_obj.storage_used_bytes += total_uploaded
            self.__user_obj.save()
            
            # Calculate upload duration
            duration = time.time() - start_time
            
            # Cleanup upload session
            del self.__active_uploads[upload_id]
            
            logger.log(severity['INFO'], f"STREAMING UPLOAD: Successfully finalized {upload_id}, blob_id={assigned_blob_id}, duration={duration:.2f}s")
            return {
                'success': True, 
                'blob_id': assigned_blob_id,
                'uploaded_size': total_uploaded,
                'duration': duration
            }
            
        except Exception as e:
            logger.log(severity['ERROR'], f"Failed to finalize streaming upload {upload_id}: {str(e)}")
            # Cleanup failed session
            if upload_id in self.__active_uploads:
                del self.__active_uploads[upload_id]
            return {'success': False, 'error': 'Failed to finalize upload'}

    def cancel_streaming_upload(self, upload_id):
        """Cancel an ongoing streaming upload and cleanup all staged blocks"""
        try:
            if upload_id not in self.__active_uploads:
                logger.log(severity['WARNING'], f"Upload session {upload_id} not found for cancellation")
                return {'success': False, 'error': 'Upload session not found'}
            
            upload_session = self.__active_uploads[upload_id]
            blob_client = upload_session['blob_client']
            blob_name = upload_session['blob_name']
            uploaded_blocks = upload_session['uploaded_blocks']
            uploaded_size = upload_session['uploaded_size']
            start_time = upload_session['start_time']
            
            logger.log(severity['INFO'], f"STREAMING UPLOAD: Cancelling {upload_id}, cleaning up {len(uploaded_blocks)} staged blocks")
            
            # Clean up all staged blocks from Azure (best effort - some may not exist yet)
            cleanup_errors = []
            for block_id in uploaded_blocks:
                try:
                    # Note: Azure doesn't provide direct block deletion, 
                    # staged blocks will be automatically cleaned up by Azure after some time
                    # We can't explicitly delete individual staged blocks
                    pass
                except Exception as e:
                    cleanup_errors.append(f"Block {block_id}: {str(e)}")
            
            # Calculate duration for logging
            duration = time.time() - start_time
            
            # Remove upload session from tracking
            del self.__active_uploads[upload_id]
            
            logger.log(severity['INFO'], f"STREAMING UPLOAD: Cancelled {upload_id}, duration={duration:.2f}s, uploaded_size={uploaded_size}")
            
            return {
                'success': True,
                'cancelled': True,
                'uploaded_size': uploaded_size,
                'duration': duration,
                'message': 'Upload cancelled successfully',
                'cleanup_errors': cleanup_errors if cleanup_errors else None
            }
            
        except Exception as e:
            logger.log(severity['ERROR'], f"Failed to cancel streaming upload {upload_id}: {str(e)}")
            # Force cleanup of session even if error occurred
            if upload_id in self.__active_uploads:
                del self.__active_uploads[upload_id]
            return {'success': False, 'error': f'Failed to cancel upload: {str(e)}'}

    def get_active_upload_sessions(self):
        """Get list of all active upload sessions for this user"""
        try:
            active_sessions = []
            for upload_id, session in self.__active_uploads.items():
                active_sessions.append({
                    'upload_id': upload_id,
                    'file_name': session['file_name'],
                    'blob_name': session['blob_name'],
                    'total_size': session['total_size'],
                    'uploaded_size': session['uploaded_size'],
                    'uploaded_blocks': len(session['uploaded_blocks']),
                    'start_time': session['start_time'],
                    'duration': time.time() - session['start_time']
                })
            
            logger.log(severity['DEBUG'], f"ACTIVE UPLOADS: User {self.__user_name} has {len(active_sessions)} active sessions")
            return {'success': True, 'active_sessions': active_sessions}
            
        except Exception as e:
            logger.log(severity['ERROR'], f"Failed to get active upload sessions: {str(e)}")
            return {'success': False, 'error': 'Failed to get active sessions'}

    # =============================================================================
    # DOWNLOAD STREAMING METHODS WITH CANCELLATION SUPPORT
    # =============================================================================

    def get_blob_stream(self, blob_id):
        """Get a streaming blob client for downloading without range"""
        try:
            if not self.__blob_id_exists(blob_id):
                logger.log(severity['ERROR'], f"Blob {blob_id} not found")
                return None
            
            blob_name = self.__blob_obj_dict[blob_id].blob_name
            blob_client = self.__container_client.get_blob_client(blob_name)
            
            logger.log(severity['DEBUG'], f"DOWNLOAD STREAM: Creating stream for blob {blob_id} ({blob_name})")
            return blob_client.download_blob()
            
        except Exception as e:
            logger.log(severity['ERROR'], f"Failed to get blob stream for {blob_id}: {str(e)}")
            return None

    def get_blob_stream_range(self, blob_id, start, end):
        """Get a streaming blob client for downloading with byte range"""
        try:
            if not self.__blob_id_exists(blob_id):
                logger.log(severity['ERROR'], f"Blob {blob_id} not found")
                return None
            
            blob_name = self.__blob_obj_dict[blob_id].blob_name
            blob_client = self.__container_client.get_blob_client(blob_name)
            
            logger.log(severity['DEBUG'], f"DOWNLOAD STREAM: Creating range stream for blob {blob_id} ({blob_name}), range {start}-{end}")
            return blob_client.download_blob(offset=start, length=end - start + 1)
            
        except Exception as e:
            logger.log(severity['ERROR'], f"Failed to get blob stream range for {blob_id}: {str(e)}")
            return None

    def cancel_blob_download(self, blob_id, download_session_id=None):
        """Cancel an ongoing blob download
        
        Note: Since Azure downloads are direct HTTP streams, we can't directly cancel 
        them from the server side. This method mainly serves to clean up any 
        server-side tracking of download sessions if implemented.
        
        The actual cancellation happens on the client side using AbortController.
        """
        try:
            logger.log(severity['INFO'], f"DOWNLOAD CANCEL: Request to cancel download for blob {blob_id}")
            
            # If we ever implement server-side download session tracking, 
            # cleanup logic would go here
            if download_session_id:
                logger.log(severity['DEBUG'], f"DOWNLOAD CANCEL: Cleaning up session {download_session_id}")
                # Future: cleanup any server-side download session state
            
            return {
                'success': True,
                'cancelled': True,
                'message': 'Download cancellation processed (client-side cancellation required)'
            }
            
        except Exception as e:
            logger.log(severity['ERROR'], f"Failed to process download cancellation for {blob_id}: {str(e)}")
            return {'success': False, 'error': f'Failed to cancel download: {str(e)}'}
