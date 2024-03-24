# import sys
# sys.path.append("...")

from azure.storage.blob import ContainerClient
from main.models import UserInfo

# import shared_variable
from .Blob import Blob
from logger import logger

import time

class Container:
    def __init__(self, container_name=None, blob_service_client=None):
        self.__container_name = container_name
        self.__blob_service_client = blob_service_client
        self.__container_list = None

        if self.__container_name != None:
            self.__container_list = set(UserInfo.objects.values_list('container_name', flat=True))

        # print("Container list : ", end=" ")
        # for _ in self.__container_list:
        #     print(_, end=' : ')
        # print()


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
        container_instance = UserInfo.objects.get(Container=self.__container_name)
        container_instance.delete()

        #update container_list
        self.__container_list.remove(self.__container_name)
        

    def container_create(self, user_obj):
        operation_status = False
        if self.__container_exists():
            logger.info("CONTAINET ALREADY EXISTS")
        else:
            try:
                '''
                Azure API call to create a container
                '''
                # # Instantiate a ContainerClient
                # container_client = self.__blob_service_client.get_container_client(self.__container_name)
                # container_client.create_container()
                
                self.__add_to_db(user_obj)
                operation_status = True
                
            except Exception as error:
                logger.error("CONTAINER CREATE EXCEPTION")
        return operation_status
        

    def container_delete(self):
        operation_status = 0
        if self.__container_exists():
            try:
                '''
                Azure API call to delete a container
                '''    
                # # Instantiate a ContainerClient
                # container_client = self.__blob_service_client.get_container_client(self.__container_name)
                # container_client.delete_container()
                
                '''
                ============================================================
                Delete Container API takes some time to delete a container
                ============================================================
                '''
                operation_status = 1
                #shared_variable.increment_api_call_counter2()
                
                self.__delete_from_db()

                time.sleep(2)
                logger.info("delete_container :: SUCCESS")
            except Exception as error:
                logger.error("CONTAINER DELETE EXCEPTION")
        else:
            logger.error("CONTAINER NOT PRESENT")
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