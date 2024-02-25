from azure.storage.blob import ContainerClient

import shared_variable
import azure_api.blob

import time

class Container:
    def __init__(self, blob_service_client):
        self.blob_service_client = blob_service_client
        self.container_dict = dict()


    def get_list(self):
        '''
        Azure API call to return list of containers
        '''
        print("get_container_dict")
        return self.container_dict.keys()
    

    # def container_exists(self, container_name):
        # return container_name in self.container_dict
    

    def container_create(self, container_name):    
        operation_status = False
        
        if self.container_exists(container_name):
            print("Container Already Exists")
        else:
            try:
                '''
                Azure API call to create a container
                '''
                # Instantiate a ContainerClient
                container_client = self.blob_service_client.get_container_client(container_name)
                container_client.create_container()
                
                #update container list
                self.container_dict[container_name] = 1    
                operation_status = True
                
                shared_variable.increment_api_call_counter2()
                print("Container Creating :: SUCCESS")
            
            except Exception as error:
                print("CONTAINER CREATE ERROR : \n", error)
            
        return operation_status
        
   
    def container_delete(self, container_name):
        operation_status = 0
        
        # FOR TESTING PURPOSE ONLY
        # REMOVE THIS
        self.container_dict[container_name] = 1
        
        if self.container_exists(container_name):
            try:
                '''
                Azure API call to delete a container
                '''    
                # Instantiate a ContainerClient
                container_client = self.blob_service_client.get_container_client(container_name)
                container_client.delete_container()
                
                #update container list
                del self.container_dict[container_name]    
                operation_status = 1
                
                shared_variable.increment_api_call_counter2()
                '''
                ============================================================
                Delete Container API takes some time to delete a container
                ============================================================
                '''
                time.sleep(5)
                print("delete_container :: SUCCESS :: ")
            except Exception as error:
                print("CONTAINER DELETE ERROR : \n", error)
        else:
            print("contained not found")
        
        return operation_status 

    
    def delete_all(self):
        ''' 
        AZURE API call to delete all containers for a user
        '''
        pass
    
    def blob(self, container_name):
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_obj = azure_api.blob.Blob(container_client, container_name)
        shared_variable.increment_api_call_counter()
        return blob_obj