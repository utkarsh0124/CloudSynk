from logging import exception
from azure.storage.blob import ContainerClient
from main.models import UserInfo

from django.contrib.auth.models import User

# import shared_variable
from .Blob import Blob, SampleBlob
from storage_webapp import logger, severity

import time


class Container:
    def __init__(self, container_name=None, blob_service_client=None):
        self.__container_name = container_name
        self.__blob_service_client = blob_service_client
        self.__container_list = None

        if self.__container_name != None:
            self.__container_list = set(UserInfo.objects.values_list('container_name', flat=True))

        logger.log(severity['INFO'], "Container Object Created : {}".format(self.__container_name))


    def __container_exists(self):
        return self.__container_name in self.__container_list


    def __add_to_db(self, user_obj):
        new_container = UserInfo()

        new_container.container_name = self.__container_name
        new_container.user_type = 'REGULAR'
        
        #assign storage quota based on user_type
        #standard user - 5GB, Premium user - 10GB
        new_container.storage_quota_kb = 4883000 #5GB
        new_container.total_storage_size_kb = 0 # total storage used
        new_container.user = user_obj

        new_container.save()
        
        #update container_list
        self.__container_list.add(self.__container_name)


    def __delete_from_db(self):
        container_instance = UserInfo.objects.get(container_name=self.__container_name)
        
        #delete user
        container_instance.user.delete()
    
        container_instance.delete()

        #update container_list
        self.__container_list.remove(self.__container_name)
        

    def container_create(self, user_obj):
        operation_status = False
        if self.__container_exists():
            logger.log(severity['INFO'], "CONTAINET ALREADY EXISTS")
        else:
            try:
                '''
                Azure API call to create a container
                '''
                container_client = self.__blob_service_client.get_container_client(self.__container_name)
                container_client.create_container()
                
                self.__add_to_db(user_obj)
                operation_status = True
                
            except Exception as error:
                logger.log(severity['ERROR'], "CONTAINER CREATE EXCEPTION : {}".format(error))
        return operation_status
        

    def container_delete(self):
        operation_status = 0
        if self.__container_exists():
            try:
                '''
                Azure API call to delete a container
                '''
                container_client = self.__blob_service_client.get_container_client(self.__container_name)
                container_client.delete_container()
                
                
                operation_status = 1
                #shared_variable.increment_api_call_counter2()
                
                # delete blob entries from DB
                blob_instance = self.blob()
                blob_instance.delete_all()

                # Delete container from DB
                self.__delete_from_db()

                '''
                ============================================================
                Delete Container API takes some time to delete a container
                ============================================================
                '''
                time.sleep(2)
                
                logger.log(severity['INFO'], "delete_container :: SUCCESS")
            except Exception as error:
                logger.log(severity['ERROR'], "CONTAINER DELETE EXCEPTION : {}".format(error))
        else:
            logger.log(severity['ERROR'], "CONTAINER NOT PRESENT")
        return operation_status 

    
    def delete_all(self):
        ''' 
        AZURE API call to delete all containers for a user
        '''
        pass
    

    def blob(self):
        container_client = self.__blob_service_client.get_container_client(self.__container_name)
        blob_obj = Blob(container_client, self.__container_name)
        #shared_variable.increment_api_call_counter()
        return blob_obj
    


class SampleContainer:
    def __init__(self, container_name=None, blob_service_client=None):
        self.__container_name = container_name
        self.__blob_service_client = blob_service_client
        self.__container_list = None

        if self.__container_name != None:
            self.__container_list = set(UserInfo.objects.values_list('container_name', flat=True))

        logger.log(severity['INFO'], "Container Object Created : {}".format(self.__container_name))

    def __container_exists(self):
        return self.__container_name in self.__container_list

    def __add_to_db(self, user_obj):
        new_container = UserInfo()

        new_container.container_name = self.__container_name
        new_container.user_type = 'REGULAR'
        
        #assign storage quota based on user_type
        #standard user - 5GB, Premium user - 10GB
        new_container.storage_quota_kb = 4883000 #5GB
        new_container.total_storage_size_kb = 0 # total storage used
        new_container.user = user_obj

        new_container.save()
        
        #update container_list
        self.__container_list.add(self.__container_name)

    def __delete_container_from_db(self, user_obj):
        delete_success = False
        try:
            # Delete all blobs from container
            blob_obj = self.get_blob_obj(user_obj)
            if not blob_obj.delete_all_blobs():
                logger.log(severity['ERROR'], "BLOB DELETE ALL EXCEPTION")
                delete_success=False
            else:
                # Delete Container from user table DB
                user_instance = UserInfo.objects.get(container_name=self.__container_name)
                user_instance.delete()
                
                #update container_list
                self.__container_list.remove(self.__container_name)

                delete_success=True
        except Exception as error:
            logger.log(severity['ERROR'], "SAMPLE CONTAINER DELETE EXCEPTION : {}".format(error))
            delete_success=False
        return delete_success
    
    
    def container_create(self, user_obj):
        operation_status = False
        if self.__container_exists():
            logger.log(severity['INFO'], "CONTAINER ALREADY EXISTS")
        else:
            '''
            Azure API call to create a container
            '''
            self.__add_to_db(user_obj)
        return operation_status 

    def container_delete(self, user_obj):
        delete_success=False
        ''' 
        AZURE API call to delete all containers for a user
        '''
        try:
            if not self.__delete_container_from_db(user_obj):
                logger.log(severity['ERROR'], "SAMPLE CONTAINER DELETE EXCEPTION")
            else:
                delete_success=True
        except Exception as error:
            logger.log(severity['ERROR'], "SAMPLE CONTAINER DELETE ALL EXCEPTION : {}".format(error))
        return delete_success
    
    def get_blob_obj(self, user_obj):
        container_client = self.__blob_service_client.get_container_client(self.__container_name)
        blob_obj = SampleBlob(user_obj, container_client, self.__container_name)
        #shared_variable.increment_api_call_counter()
        return blob_obj

