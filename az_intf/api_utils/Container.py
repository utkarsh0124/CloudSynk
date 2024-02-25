from azure.storage.blob import ContainerClient

import shared_variable
import Blob

import time

class Container:
    def __init__(self, container_name:str, blob_service_client=None):
        self.__container_name = container_name
        self.__blob_service_client = blob_service_client
        #get container list from local DB
        #made public for testing purpose. Change to private
        self.container_list = set()


    def __container_exists(self):
        return self.__container_name in self.container_list


    def __add_to_db(self):
        #add self.__containainer_name to db
        
        #update container_list
        self.container_list.add(self.__container_name)
        pass


    def __delete_from_db(self):
        #delete self.__container_name from db

        #update container_list
        self.container_list.remove(self.__container_name)
        pass
        

    def container_create(self):
        operation_status = False
        if self.__container_exists():
            print("CONTAINET ALREADY EXISTS")
        else:
            try:
                '''
                Azure API call to create a container
                '''
                # Instantiate a ContainerClient
                container_client = self.__blob_service_client.get_container_client(self.__container_name)
                container_client.create_container()
                
                self.__add_to_db()
                operation_status = True
                
                shared_variable.increment_api_call_counter2()
                print("Container Creating :: SUCCESS")
            
            except Exception as error:
                print("CONTAINER CREATE ERROR : ", error)
        return operation_status
        

    def container_delete(self):
        operation_status = 0
        if self.__container_exists():
            try:
                '''
                Azure API call to delete a container
                '''    
                # Instantiate a ContainerClient
                container_client = self.__blob_service_client.get_container_client(self.__container_name)
                container_client.delete_container()
                
                '''
                ============================================================
                Delete Container API takes some time to delete a container
                ============================================================
                '''
                operation_status = 1
                shared_variable.increment_api_call_counter2()
                
                self.__delete_from_db()

                time.sleep(2)
                print("delete_container :: SUCCESS :: ")
            except Exception as error:
                print("CONTAINER DELETE ERROR : ", error)
        else:
            print("CONTAINER NOT PRESENT")        
        return operation_status 

    
    def delete_all(self):
        ''' 
        AZURE API call to delete all containers for a user
        '''
        pass
    

    def blob(self):
        container_client = self.__blob_service_client.get_container_client(self.__container_name)
        blob_obj = Blob.Blob(container_client, self.__container_name)
        shared_variable.increment_api_call_counter()
        return blob_obj