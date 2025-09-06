from .api_utils.Container import Container
from storage_webapp import logger, severity

CONTAINER_INSTANCE = None

def init_container(user_obj, username:str, container_name:str, email_id):
    logger.log(severity['DEBUG'], "INIT CONTAINER : {}".format(username))
    try:
        Container.container_create(user_obj,
                        username=username,
                        container_name=container_name,
                        email_id=email_id)
    except Exception as error:
        logger.log(severity['ERROR'], "INIT CONTAINER EXCEPTION : {}".format(error))
        return False
    return True

def get_container_instance(username:str):
    logger.log(severity['DEBUG'], "GET CONTAINER INSTANCE : {}".format(username))
    global CONTAINER_INSTANCE
    if not CONTAINER_INSTANCE:
        logger.log(severity['DEBUG'], "CREATING NEW CONTAINER INSTANCE")
        CONTAINER_INSTANCE = Container(username)
    return CONTAINER_INSTANCE

def del_container_instance(username:str):
    logger.log(severity['DEBUG'], "DEL CONTAINER INSTANCE : {}".format(username))
    global CONTAINER_INSTANCE
    if CONTAINER_INSTANCE:
        logger.log(severity['DEBUG'], "DELETING CONTAINER INSTANCE")
        CONTAINER_INSTANCE = None
    return True

def user_exists(username:str):
    logger.log(severity['DEBUG'], "USER EXISTS CHECK : {}".format(username))
    return Auth.Auth.user_exists(username) or Container.user_exists(username)