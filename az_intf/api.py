from .api_utils import Container, Auth

# Singleton 
class Api:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, container_name):
        print("\n\n     New API Instance Created \n\n")
        self.__container_name = container_name
        self.__container_obj = None
        self.__blob_obj = None

        print("ESTABLISHING CONNECTION TO AZURE")
        self.__azure_conn = Auth.Auth()
        
        self.__client = self.__azure_conn.auth_api()
        print("SUCCESS")

        self.__container_obj = Container.Container(self.__container_name, self.__client)
        self.__blob_obj = self.__container_obj.blob()
    
            
    def add_container(self, user_obj):
        if self.__container_obj:
            self.__container_obj.container_create(user_obj)
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
    

    def get_blob_size(self, blob_path:str):
        return 0


    def list_blob(self):
        return self.__container_obj.blob().get_list()


# Global variable
API_INSTANCE = None

def get_api_instance(container_name):
    global API_INSTANCE
    if API_INSTANCE == None:
        API_INSTANCE = Api(container_name)
    return API_INSTANCE

def del_api_instance():
    global API_INSTANCE
    if API_INSTANCE != None:
        del API_INSTANCE
        API_INSTANCE=None
    
    print("\n\n     Deleting API Instance\n\n")