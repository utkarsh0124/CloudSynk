import time

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
    
    def get_blob_list(self):
        try:
            # use filter to get all blobs for this user; self.__user_obj.user_id is the User PK
            blobs = Blob.objects.filter(user_id=self.__user_obj.user_id)
        except Exception as e:
            # unexpected errors (DB issues, etc.)
            logger.log(severity['ERROR'], "GET BLOB LIST EXCEPTION : {}".format(e))            
            return []
        return [
            {
                'blob_id' : b.blob_id,
                'blob_name': b.blob_name,
                'size': b.blob_size,
                'uploaded_at': b.creation_time,
                'download_url': f'/download/{b.blob_name}'  # adjust as needed
            }
            for b in blobs
        ]
    
    def get_blob_size(self, blob_id:str):
        if not self.__blob_id_exists(blob_id):
            logger.log(severity['INFO'], "BLOB DOES NOT EXIST")
            return 0
        return self.__blob_obj_dict[blob_id].blob_size

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

            # Temporary server side AZURE API call to create a blob for a user 
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
                    
                    # with open(blob_file, "rb") as data:
                    #     blob_client.upload_blob(data, overwrite=True)
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

            size = self.get_blob_size(blob_id)
            # update and save this user's storage usage
            self.__user_obj.storage_used_bytes = max(0, self.__user_obj.storage_used_bytes - size)
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
