import os
from azure.storage.blob import BlobServiceClient
from storage_webapp import logger, severity

class Auth:
    def __init__(self):
        self.conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        
    def __auth_api(self):
        blob_service_client = BlobServiceClient.from_connection_string(self.conn_str)
        return blob_service_client

    def auth_api(self): 
        try:
            self.blob_service_client = self.__auth_api()
            logger.log(severity['INFO'], "AZURE AUTHENTICATION SUCCESSFUL")
        except Exception as error:
            logger.log(severity['ERROR'], "AZURE AUTHENTICATION FAILED")
        return self.blob_service_client