from .api_utils import Container, Auth
from storage_webapp import logger, severity

from apiConfig import AZURE_API_DISABLE

# Global Definition
API_INSTANCE = None


# Singleton Class
class ApiUtils:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    

    def __init__(self, container_name:str):
        if AZURE_API_DISABLE:
            self.__container_obj = Container.SampleContainer(
                                                    container_name,
                                                    Auth.Auth().auth_api()
                                                    )
            self.__blob_obj = self.__container_obj.blob()
        else:
            self.__container_obj = Container.Container(
                                                    container_name,
                                                    Auth.Auth().auth_api()
                                                    )
            self.__blob_obj = self.__container_obj.blob()

    def add_container(self, user_obj):
        if self.__container_obj:
            self.__container_obj.container_create(user_obj)
        else:
            logger.log(severity['ERROR'], 'CONTAINER OBJECT IS NONE')

        
    def create_blob(self, uploaded_file, blob_path:str):
        if self.__blob_obj:
            self.__blob_obj.blob_create(uploaded_file, blob_path)
        else:
            logger.log(severity['ERROR'], 'BLOB OBJECT IS NONE')


    def delete_container(self):
        if self.__container_obj:
            self.__container_obj.container_delete()
        else:
            logger.log(severity['ERROR'], 'CONTAINER OBJECT IS NONE')
        

    def delete_blob(self, blob_path:str):
        if self.__blob_obj:
            self.__blob_obj.blob_delete(blob_path)
        else:
            logger.log(severity['ERROR'], 'BLOB OBJECT IS NONE')
    

    def get_blob_size(self, blob_path:str):
        return 0


    def list_blob(self):
        return self.__container_obj.blob().get_list()


def get_api_instance(container_name:str):
    global API_INSTANCE
    if API_INSTANCE == None:
        logger.log(severity['INFO'], 'INITIALIZING WITH CONTAINER {}'.format(container_name))
        API_INSTANCE = ApiUtils(container_name)
    # global API_LOG_INSTANCE
    # if API_LOG_INSTANCE == None:
    #     API_LOG_INSTANCE = logger.get_api_log_instance()

    # API_LOG_INSTANCE
    return API_INSTANCE


def del_api_instance():
    global API_INSTANCE
    if API_INSTANCE != None:
        del(API_INSTANCE)
        API_INSTANCE=None
    logger.log(severity['INFO'], 'API INSTANCE DELETED')
