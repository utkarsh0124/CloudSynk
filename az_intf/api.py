from db_user import DbUser
from api_utils import Container, Auth

class Api:
    def __init__(self, container_name):
        self.__container_name = container_name
        self.__user_obj = DbUser.DbUser()
        self.__container_obj = None
        self.__blob_obj = None

        if self.__user_obj.user_auth_local():
            #Authenticating user locally"   
            print("ESTABLISHING CONNECTION TO AZURE")
            self.__azure_conn = Auth.Auth()
            
            self.__client = self.__azure_conn.auth_api()
            print("SUCCESS")

            self.__container_obj = Container.Container(self.__container_name, self.__client)
            self.__blob_obj = self.__container_obj.blob()

            
    def add_container(self):
        if self.__container_obj:
            self.__container_obj.container_create()
        else:
            print("Container Object is None")
        

    def create_blob(self, blob_path):
        if self.__blob_obj:
            self.__blob_obj.blob_create(blob_path)
        else:
            print("Blob Object is None")

    def delete_container(self):
        if self.__container_obj:
            self.__container_obj.container_delete()
        else:
            print("Container Object is None")
        

    def delete_blob(self, blob_path):
        if self.__blob_obj:
            self.__blob_obj.blob_delete(blob_path)
        else:
            print("Blob Object is None")


    def assign_container(self, username:str):
        #get new container assigned to the user from azure
        container_name = username + "_container"
        return container_name


    def get_blob_size(blob_path:str):
        pass

    
    def list_blob(container_name:str):
        pass