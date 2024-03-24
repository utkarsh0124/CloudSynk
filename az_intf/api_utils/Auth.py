import os
from azure.storage.blob import BlobServiceClient
from logger import logger


class Auth:
    def __init__(self, conn_str=None):
        self.conn_str = conn_str
        self.auth = False
        self.blob_service_client = None
    

    def __auth_api(self):
        '''
        AZURE API call
        ''' 
        blob_service_client = BlobServiceClient.from_connection_string(self.conn_str)
        
        return blob_service_client


    def auth_api(self): 
        self.conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        
        try:
            self.blob_service_client = self.__auth_api()
        except Exception as error:
            logger.error("AZURE AUTHENTICATION FAILED")

        return self.blob_service_client