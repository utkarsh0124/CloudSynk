import time
import base64

# from django.contrib.auth.models import User
from azure.storage.blob import ContainerClient, BlobServiceClient
from main.models import UserInfo, Blob
from az_intf.api_utils import utils as app_utils
from main.subscription_config import SUBSCRIPTION_CHOICES, SUBSCRIPTION_VALUES
from storage_webapp import logger, severity
from storage_webapp.settings import DEFAULT_SUBSCRIPTION_AT_INIT
from .utils import AZURE_STORAGE_ACCOUNT_NAME, AZURE_STORAGE_ACCOUNT_KEY, AZURE_STORAGE_ENDPOINT_SUFFIX


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
            logger.log(severity['INFO'], "CONTAINER DOES NOT EXIST")
            logger.log(severity['ERROR'], "FAILED TO INITIALIZE CONTAINER CLIENT")
            # Object not created
            return
        self.__container_client = self.__service_client.get_container_client(self.__user_obj.container_name)

        # dictionary of key=blob name, value=blob object
        self.__blob_obj_dict = {blob_obj.blob_id: blob_obj for blob_obj in Blob.objects.filter(user_id=self.__user_obj.user_id)}
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
                    'email_id': email_id
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

    def validate_new_blob_addition(self, new_blob_size, blob_name):
        # validate against user's quota
        if self.__user_obj.storage_used_bytes + new_blob_size > self.__user_obj.storage_quota_bytes:
            logger.log(severity['DEBUG'], "BLOB VALIDATION FAILED : User Name : {}, Used : {}, Quota : {}, New Blob Size : {}".format(self.__user_name,
                       self.__user_obj.storage_used_bytes,
                       self.__user_obj.storage_quota_bytes,
                       new_blob_size))
            return (False, "Storage quota exceeded. Please delete some files before uploading new ones or Upgrade your Subscription")
        # validate blob name uniqueness
        if self.__blob_name_exists(blob_name):
            logger.log(severity['DEBUG'], "BLOB VALIDATION FAILED : Blob Name Already Exists : {}".format(blob_name))
            return (False, "Blob name already exists. Please use a different file.")
        return (True, "Success")    

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

    def get_upload_blob_sas_url(self, blob_id, expiry_hours=1):
        try:
            if self.__blob_id_exists(blob_id):
                logger.log(severity['INFO'], "BLOB ALREADY EXISTS")
                return None
            container_name = self.__user_obj.container_name
            blob_name = self.__blob_obj_dict[blob_id].blob_name
            sas_url = app_utils.get_blob_sas_url(
                container_name=container_name,
                blob_name=blob_name,
                permission="w",
                expiry_hours=expiry_hours
            )
            if sas_url is None:
                logger.log(severity['ERROR'], "GET BLOB SAS URL FAILED")
                return None
            logger.log(severity['INFO'], "GET BLOB SAS URL SUCCESS")
            return sas_url
        except Exception as error:
            logger.log(severity['ERROR'], "GET BLOB SAS URL EXCEPTION : {}".format(error))
        return None

    # def get_download_blob_sas_url(self, blob_id, expiry_hours=1):
    #     try:
    #         if not self.__blob_id_exists(blob_id):
    #             logger.log(severity['ERROR'], "BLOB DOES NOT EXIST FOR DOWNLOAD")
    #             return None
    #         container_name = self.__user_obj.container_name
    #         blob_name = self.__blob_obj_dict[blob_id].blob_name
    #         sas_url = app_utils.get_blob_sas_url(
    #             container_name=container_name,
    #             blob_name=blob_name,
    #             permission="r",
    #             expiry_hours=expiry_hours
    #         )
    #         if sas_url is None:
    #             logger.log(severity['ERROR'], "GET DOWNLOAD BLOB SAS URL FAILED")
    #             return None
    #         logger.log(severity['INFO'], "GET DOWNLOAD BLOB SAS URL SUCCESS")
    #         return sas_url
    #     except Exception as error:
    #         logger.log(severity['ERROR'], "GET DOWNLOAD BLOB SAS URL EXCEPTION : {}".format(error))
    #     return None

    # def get_blob_info(self, blob_id):
    #     """Get blob information by blob_id"""
    #     try:
    #         if not self.__blob_id_exists(blob_id):
    #             logger.log(severity['ERROR'], "BLOB DOES NOT EXIST")
    #             return None
    #         blob_obj = self.__blob_obj_dict[blob_id]
    #         return {
    #             'blob_id': blob_obj.blob_id,
    #             'blob_name': blob_obj.blob_name,
    #             'blob_size': blob_obj.blob_size,
    #             'blob_type': blob_obj.blob_type,
    #             'creation_time': blob_obj.creation_time,
    #             'last_modification_time': blob_obj.last_modification_time
    #         }
    #     except Exception as error:
    #         logger.log(severity['ERROR'], "GET BLOB INFO EXCEPTION : {}".format(error))
    #     return None

    def get_blob_stream(self, blob_id):
        """Get blob stream for direct download using service client"""
        try:
            if not self.__blob_id_exists(blob_id):
                logger.log(severity['ERROR'], "BLOB DOES NOT EXIST FOR DOWNLOAD")
                return None
                
            if self.__container_client is None:
                logger.log(severity['ERROR'], "CONTAINER CLIENT NOT INITIALIZED")
                return None
                
            blob_name = self.__blob_obj_dict[blob_id].blob_name
            blob_client = self.__container_client.get_blob_client(blob_name)
            
            # Get the blob download stream
            download_stream = blob_client.download_blob()
            
            logger.log(severity['INFO'], "GET BLOB STREAM SUCCESS : Blob ID : {}, Blob Name : {}".format(blob_id, blob_name))
            return download_stream
            
        except Exception as error:
            logger.log(severity['ERROR'], "GET BLOB STREAM EXCEPTION : {}".format(error))
            return None

    def get_blob_stream_range(self, blob_id, start_byte=0, end_byte=None):
        """Get blob stream with range support for resumable downloads"""
        try:
            if not self.__blob_id_exists(blob_id):
                logger.log(severity['ERROR'], "BLOB DOES NOT EXIST FOR DOWNLOAD")
                return None
                
            if self.__container_client is None:
                logger.log(severity['ERROR'], "CONTAINER CLIENT NOT INITIALIZED")
                return None
                
            blob_name = self.__blob_obj_dict[blob_id].blob_name
            blob_client = self.__container_client.get_blob_client(blob_name)
            
            # Calculate length for range request
            if end_byte is None:
                blob_properties = blob_client.get_blob_properties()
                end_byte = blob_properties.size - 1
                
            length = end_byte - start_byte + 1
            
            # Download with range
            download_stream = blob_client.download_blob(offset=start_byte, length=length)
            
            logger.log(severity['INFO'], "GET BLOB STREAM RANGE SUCCESS : Blob ID : {}, Blob Name : {} (bytes {}-{})".format(blob_id, blob_name, start_byte, end_byte))
            return download_stream
            
        except Exception as error:
            logger.log(severity['ERROR'], "GET BLOB STREAM RANGE EXCEPTION : {}".format(error))
            return None

    def store_upload_chunk(self, upload_id, chunk_index, chunk_data, file_name, total_chunks, total_size):
        """Store individual upload chunk"""
        try:
            if self.__container_client is None:
                logger.log(severity['ERROR'], "CONTAINER CLIENT NOT INITIALIZED")
                return False
                
            # Create temp blob name for chunk
            chunk_blob_name = "temp_uploads/{}/chunk_{:06d}".format(upload_id, chunk_index)
            blob_client = self.__container_client.get_blob_client(chunk_blob_name)
            
            # Upload chunk
            blob_client.upload_blob(chunk_data, overwrite=True)
            
            # Store metadata about the upload
            metadata = {
                'upload_id': upload_id,
                'chunk_index': str(chunk_index),
                'total_chunks': str(total_chunks),
                'file_name': file_name,
                'total_size': str(total_size),
                'timestamp': str(time.time())
            }
            blob_client.set_blob_metadata(metadata)
            
            logger.log(severity['INFO'], "CHUNK UPLOAD SUCCESS : Upload ID : {}, Chunk : {}".format(upload_id, chunk_index))
            return True
            
        except Exception as error:
            logger.log(severity['ERROR'], "CHUNK UPLOAD EXCEPTION : {}".format(error))
            return False

    def finalize_chunked_upload(self, upload_id, file_name, total_size):
        """Combine chunks into final blob"""
        try:
            if self.__container_client is None:
                logger.log(severity['ERROR'], "CONTAINER CLIENT NOT INITIALIZED")
                return None
                
            # List all chunks for this upload
            chunk_prefix = "temp_uploads/{}/chunk_".format(upload_id)
            chunks = []
            
            for blob in self.__container_client.list_blobs(name_starts_with=chunk_prefix):
                chunks.append(blob)
            
            # Sort chunks by index
            chunks.sort(key=lambda x: int(x.metadata.get('chunk_index', 0)))
            
            # Create final blob
            final_blob_name = "{}_{}".format(int(time.time()), file_name)
            final_blob_client = self.__container_client.get_blob_client(final_blob_name)
            
            # Optimized approach: Use Azure's block blob composition instead of downloading/re-uploading
            try:
                print(f"Starting efficient combination for {len(chunks)} chunks...")
                # Method 1: Try to use block blob composition for efficient combination
                self._combine_chunks_efficiently(chunks, final_blob_client, total_size)
                print("Efficient combination completed successfully")
            except Exception as e:
                # Fallback to original method if efficient method fails
                print(f"Efficient combination failed: {e}, falling back to original method")
                self._combine_chunks_fallback(chunks, final_blob_client)
            
            # Clean up chunks (can be done in parallel)
            print("Starting chunk cleanup...")
            self._cleanup_chunks_parallel(chunks)
            print("Chunk cleanup completed")
            
            # Add to database
            result, blob_id = self.__add_blob_to_db(final_blob_name, total_size, "file")
            if not result:
                logger.log(severity['ERROR'], "FINALIZE CHUNKED UPLOAD : Failed to add to database")
                return None
            
            logger.log(severity['INFO'], "CHUNKED UPLOAD FINALIZED : Upload ID : {} -> Blob ID : {}".format(upload_id, blob_id))
            return blob_id
            
        except Exception as error:
            logger.log(severity['ERROR'], "FINALIZE CHUNKED UPLOAD EXCEPTION : {}".format(error))
            return None

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

    def blob_create(self,blob_name:str, blob_size_bytes:int, blob_type:str="file", blob_file=None):
        # add debug log using format print
        logger.log(severity['DEBUG'], "BLOB CREATE : Blob Name : {}, Blob Size Bytes : {}, Blob Type : {}".format(blob_name, blob_size_bytes, blob_type))
        assigned_blob_id = None
        try:
            if self.__blob_name_exists(blob_name):
                logger.log(severity['INFO'], "BLOB ALREADY EXISTS")
                return (False, assigned_blob_id)
            # add debug log
            logger.log(severity['DEBUG'], "BLOB CREATE : Checking quota for user : {}, Used : {}, Quota : {}".format(self.__user_name,
                       self.__user_obj.storage_used_bytes,
                       self.__user_obj.storage_quota_bytes))

            # check against the user's quota
            if self.__user_obj.storage_used_bytes + blob_size_bytes >= self.__user_obj.storage_quota_bytes:
                logger.log(severity['INFO'], "STORAGE EXCEEDED")
                return (False, assigned_blob_id)

            # add debug log with format print
            logger.log(severity['DEBUG'], "BLOB CREATE : Quota OK for user : {}, Used : {}, Quota : {}".format(self.__user_name,
                       self.__user_obj.storage_used_bytes,
                       self.__user_obj.storage_quota_bytes))
            
            # update and save user's storage usage
            self.__user_obj.storage_used_bytes += blob_size_bytes
            self.__user_obj.save()

            # server side AZURE API call to create a blob for a user 
            #---------------------------------------------------------------------------
            if self.__container_client is not None:
                if not blob_file:
                    logger.log(severity['INFO'], "BLOB CREATE : No file provided, creating empty blob")
                    self.__user_obj.delete()
                    return (False, None)
                else:
                    logger.log(severity['INFO'], "BLOB CREATE : Uploading provided file as blob : {}".format(blob_name))
                    blob_client = self.__container_client.get_blob_client(blob_name)

                    file_like = getattr(blob_file, "file", blob_file)
                    blob_client.upload_blob(file_like, overwrite=True)
                logger.log(severity['INFO'], "BLOB CREATE : Blob '{}' created in container '{}'.".format(blob_name, self.__user_obj.container_name))
            else:
                logger.log(severity['ERROR'], "BLOB CREATE FAILED : CONTAINER CLIENT NOT INITIALIZED")
                self.__user_obj.delete()
                return (False, assigned_blob_id)
            #---------------------------------------------------------------------------

            #add debug log
            logger.log(severity['DEBUG'], "BLOB CREATE : Updated storage used for user : {}, New Used : {}".format(self.__user_name,
                       self.__user_obj.storage_used_bytes))

            result, assigned_blob_id = self.__add_blob_to_db(blob_name, blob_size_bytes, blob_type)
            if not result:
                logger.log(severity['ERROR'], "BLOB CREATE EXCEPTION")
                self.__user_obj.delete()
                return (False, assigned_blob_id)
        except Exception as error:
            logger.log(severity['ERROR'], "BLOB CREATE EXCEPTION : {}".format(error))
            return (False, assigned_blob_id)
        return (True, assigned_blob_id)

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

    def _combine_chunks_efficiently(self, chunks, final_blob_client, total_size):
        """
        Efficient chunk combination using streaming without loading all into memory
        """
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Use block blob for efficient combination
        block_list = []
        
        # Stream chunks directly to final blob using put_block
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            
            for i, chunk_blob in enumerate(chunks):
                block_id = f"block-{i:06d}".encode('utf-8')
                block_id_b64 = base64.b64encode(block_id).decode('utf-8')
                
                future = executor.submit(self._upload_block_from_chunk, 
                                       final_blob_client, chunk_blob, block_id_b64)
                futures[future] = block_id_b64
            
            # Collect successful blocks
            for future in as_completed(futures):
                block_id_b64 = futures[future]
                try:
                    future.result()  # Ensure the block was uploaded successfully
                    block_list.append(block_id_b64)
                except Exception as e:
                    raise Exception(f"Failed to upload block {block_id_b64}: {e}")
        
        # Commit the block list to finalize the blob
        final_blob_client.commit_block_list(block_list)
    
    def _upload_block_from_chunk(self, final_blob_client, chunk_blob, block_id):
        """
        Upload a single block by streaming from chunk blob
        """
        chunk_client = self.__container_client.get_blob_client(chunk_blob.name)
        
        # Download chunk data and upload as block
        chunk_data = chunk_client.download_blob().readall()
        final_blob_client.stage_block(block_id, chunk_data)
    
    def _combine_chunks_fallback(self, chunks, final_blob_client):
        """
        Fallback method: original approach but with better memory management
        """
        print(f"Using fallback method for {len(chunks)} chunks...")
        
        # For very large files (many chunks), use streaming upload to avoid memory issues
        if len(chunks) > 50:  # > 100MB file
            self._combine_chunks_streaming(chunks, final_blob_client)
        else:
            # Use original method for smaller files
            from io import BytesIO
            
            with BytesIO() as combined_data:
                for i, chunk_blob in enumerate(chunks):
                    if i % 10 == 0:
                        print(f"Processing chunk {i+1}/{len(chunks)}")
                    chunk_client = self.__container_client.get_blob_client(chunk_blob.name)
                    chunk_data = chunk_client.download_blob().readall()
                    combined_data.write(chunk_data)
                
                # Upload final blob
                print("Uploading final blob...")
                combined_data.seek(0)
                final_blob_client.upload_blob(combined_data, overwrite=True)
    
    def _combine_chunks_streaming(self, chunks, final_blob_client):
        """
        Stream chunks directly without loading all into memory
        """
        print("Using streaming combination for large file...")
        
        # Use Azure's block blob API for streaming
        block_list = []
        
        for i, chunk_blob in enumerate(chunks):
            if i % 10 == 0:
                print(f"Streaming chunk {i+1}/{len(chunks)}")
                
            chunk_client = self.__container_client.get_blob_client(chunk_blob.name)
            chunk_data = chunk_client.download_blob().readall()
            
            # Create block ID
            block_id = f"block-{i:06d}".encode('utf-8')
            block_id_b64 = base64.b64encode(block_id).decode('utf-8')
            
            # Stage the block
            final_blob_client.stage_block(block_id_b64, chunk_data)
            block_list.append(block_id_b64)
        
        # Commit all blocks
        print("Committing blocks...")
        final_blob_client.commit_block_list(block_list)
    
    def _cleanup_chunks_parallel(self, chunks):
        """
        Delete chunks in parallel for faster cleanup
        """
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            
            for chunk_blob in chunks:
                chunk_client = self.__container_client.get_blob_client(chunk_blob.name)
                future = executor.submit(chunk_client.delete_blob)
                futures.append(future)
            
            # Wait for all deletions to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Warning: Failed to delete chunk: {e}")
                    # Continue with other deletions even if one fails
