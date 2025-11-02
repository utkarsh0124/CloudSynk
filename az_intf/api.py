from .api_utils.Container import Container
from .api_utils import Auth
from storage_webapp import logger, severity

# Dictionary to store container instances per user for sticky sessions
CONTAINER_INSTANCES = {}

def init_container(user_obj, username:str, container_name:str, email_id):
    logger.log(severity['DEBUG'], "INIT CONTAINER : {}".format(username))
    try:
        ret = Container.container_create(user_obj,
                        username=username,
                        container_name=container_name,
                        email_id=email_id)
    except Exception as error:
        logger.log(severity['ERROR'], "INIT CONTAINER EXCEPTION : {}".format(error))
        return False
    return ret

def get_container_instance(username:str):
    logger.log(severity['DEBUG'], "GET CONTAINER INSTANCE : {}".format(username))
    global CONTAINER_INSTANCES
    
    # Check if we already have a container instance for this user
    if username not in CONTAINER_INSTANCES or CONTAINER_INSTANCES[username] is None:
        logger.log(severity['DEBUG'], "CREATING NEW CONTAINER INSTANCE FOR USER : {}".format(username))
        CONTAINER_INSTANCES[username] = Container(username)
    else:
        logger.log(severity['DEBUG'], "REUSING EXISTING CONTAINER INSTANCE FOR USER : {}".format(username))
    
    return CONTAINER_INSTANCES[username]

def del_container_instance(username:str):
    logger.log(severity['DEBUG'], "DEL CONTAINER INSTANCE : {}".format(username))
    global CONTAINER_INSTANCES
    if username in CONTAINER_INSTANCES and CONTAINER_INSTANCES[username]:
        logger.log(severity['DEBUG'], "DELETING CONTAINER INSTANCE FOR USER : {}".format(username))
        CONTAINER_INSTANCES[username] = None
    return True

def user_exists(username:str):
    logger.log(severity['DEBUG'], "USER EXISTS CHECK : {}".format(username))
    return Auth.Auth.user_exists(username) or Container.user_exists(username)