from logging import exception
from azure.storage.blob import ContainerClient
from main.models import UserInfo, Blob
from az_intf import utils as app_utils
from django.contrib.auth.models import User
from main.subscription_config import SUBSCRIPTION_CHOICES, SUBSCRIPTION_VALUES
from storage_webapp import logger, severity
import time
from storage_webapp.settings import DEFAULT_SUBSCRIPTION_AT_INIT

class Container:
    def __init__(self, username:str):
        self.__user_name = username
        self.__user_obj = UserInfo.objects.get(user_name=username)
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
        try:
            if UserInfo.objects.filter(container_name=container_name).exists():
                logger.log(severity['INFO'], "CONTAINER ALREADY EXISTS")
                return True

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
            create_success = True
        except Exception as error:
            logger.log(severity['ERROR'], "SAMPLE CONTAINER CREATE EXCEPTION : {}".format(error))
        return create_success
    
    def __blob_id_exists(self, blob_id:str):
        return blob_id in self.__blob_obj_dict.keys()

    def __blob_name_exists(self, blob_name:str):
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
    
    def blob_create(self, blob_name:str, blob_size_bytes:int, blob_type:str="file"):
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

            # add debug log
            logger.log(severity['DEBUG'], "BLOB CREATE : Quota check passed, proceeding to add blob to DB")

            # update and save user's storage usage
            self.__user_obj.storage_used_bytes += blob_size_bytes
            self.__user_obj.save()

            #add debug log
            logger.log(severity['DEBUG'], "BLOB CREATE : Updated storage used for user : {}, New Used : {}".format(self.__user_name,
                       self.__user_obj.storage_used_bytes))

            result, assigned_blob_id = self.__add_blob_to_db(blob_name, blob_size_bytes, blob_type)
            if not result:
                logger.log(severity['ERROR'], "BLOB CREATE EXCEPTION")
                return (False, assigned_blob_id)
        except Exception as error:
            logger.log(severity['ERROR'], "BLOB CREATE EXCEPTION : {}".format(error))
            return (False, assigned_blob_id)
        return (True, assigned_blob_id)

    def get_blob_list(self):
        try:
            # use filter to get all blobs for this user; self.__user_obj.user_id is the User PK
            blobs = Blob.objects.filter(user_id=self.__user_obj.user_id)
        except Exception as e:
            # unexpected errors (DB issues, etc.)
            logger.log(severity['ERROR'], "GET BLOB LIST EXCEPTION : {}".format(e))
            return []

        # return an empty list automatically if no blobs exist
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

    def blob_delete(self, blob_id):
        try:
            if not self.__blob_id_exists(blob_id):
                logger.log(severity['INFO'], "BLOB DOES NOT EXIST")
                return False

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
        ''' 
        AZURE API call to delete all containers for a user
        '''
        try:
            if not self.__delete_container_from_db():
                logger.log(severity['ERROR'], "SAMPLE CONTAINER DELETE EXCEPTION")
            else:
                delete_success=True
        except Exception as error:
            logger.log(severity['ERROR'], "SAMPLE CONTAINER DELETE ALL EXCEPTION : {}".format(error))
        return delete_success
