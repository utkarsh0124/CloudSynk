''' 
GLOBAL Variables
''' 

# __USER_AUTH:dict = {}
# __USER_LOGIN_STATUS:dict = {}
__USER:str

# def set_user_auth(user_name:str, auth:bool):
#     global __USER_AUTH
#     __USER_AUTH[user_name] = auth
# 
# def get_user_auth(user_name:str)->dict:
#     global __USER_AUTH
#     return __USER_AUTH[user_name]

# def set_user_login_status(user_name:str, status:bool):
#     global __USER_LOGIN_STATUS
#     __USER_LOGIN_STATUS[user_name]=status

# def get_user_login_status(user_name:str):
#     global __USER_LOGIN_STATUS
#     return __USER_LOGIN_STATUS[user_name]

def set_user(user_name:str):
    global __USER
    __USER=user_name

def get_user()->str:
    global __USER
    return __USER