from datetime import datetime, timedelta, timezone
import os
import random
import string

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from storage_webapp import logger, severity

from azure.storage.blob import generate_blob_sas, BlobSasPermissions

AZURE_STORAGE_ACCOUNT_NAME=os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY=os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_STORAGE_ENDPOINT_SUFFIX=os.getenv("AZURE_STORAGE_ENDPOINT_SUFFIX")
AZURE_STORAGE_CONNECTION_STRING=os.getenv("AZURE_STORAGE_CONNECTION_STRING")

def assign_container(username):
    ''' 
        Logic to create new Container name for a New User
        Azure Container Naming Rules. A container name must:
        [1] Only contain lowercase letters, numbers, and dashes (-)
        [2] Start with a letter or number
        [3] Be between 3 and 63 characters long
        [4] No uppercase, no underscores _, no special characters
    '''
    # make sure username contains only lowercase english characters, numbers and dashes
    username = ''.join(c for c in username if c.isalnum() or c == '-')
    fixed_length = 6
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=fixed_length))
    if len(username) > fixed_length:
        username = username[:fixed_length]

    container_name = username + "-" + random_string + "-container"
    container_name = container_name.lower().replace("_", "-").replace(" ", "-")
    return container_name

def user_exists(username):
    try:
        User.objects.get(username=username)
    except User.DoesNotExist:
        return False 
    return True

def username_valid(username):
    return not(username==None or username=="")

def validate_file_extension(value):
    import os
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.png', '.xlsx', '.xls', 'txt', 'zip']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension.')
    
def get_blob_sas_url(container_name, blob_name, permission="r", expiry_hours=1):
    try:
        sas_token = generate_blob_sas(
            account_name=AZURE_STORAGE_ACCOUNT_NAME,
            account_key=AZURE_STORAGE_ACCOUNT_KEY,
            container_name=container_name,
            blob_name=blob_name,
            #permission can be 'r' for read, 'w' for write, 'd' for delete, 'l' for list, 'c' for create depending on permission variable
            permission=BlobSasPermissions(read=(permission=="r"),
                                           write=(permission=="w"),
                                           delete=(permission=="d"),
                                           list=(permission=="l"),
                                           create=(permission=="c")),
            expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
        )
        upload_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.{AZURE_STORAGE_ENDPOINT_SUFFIX}/{container_name}/{blob_name}?{sas_token}"
        return upload_url
    except Exception as error:
        logger.log(severity['ERROR'], f"Failed to generate BLOB SAS URL: {error}")
        return None