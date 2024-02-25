class DbUser:
    def __init__(self, user_id=None, user_pass=None):
        self.user_id = user_id
        self.user_pass = user_pass
        self.auth = False
     
    def user_auth_local(self):
        ''' 
        Check user exists in local DB
        ''' 
        #db auth
        self.auth = True
        
        print("Checking user exists in local DB") 
        return self.auth
    
    