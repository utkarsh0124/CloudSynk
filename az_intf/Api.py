import azure_api

class Api:
    def __init__(self, container=None):
        self.container = container
        self.client = None
        try:
            _azure_conn = azure_api.azure_auth.Azure_auth()
            self.client = _azure_conn.azure_auth()
        except Exception as e:
            print("Azure API Authentication Error : ", e)
            print("=====================\nFAILED\n==================")
            
    def create_container(self):
        try:
            ctnr = azure_api.container.Container(self.client)
            ctnr.container_create(self.container)
        except exception as e:
            print("Azure API Container Creation Error : ", e)
            print("=====================\nFAILED\n==================")
    
    # def create_blob(self):