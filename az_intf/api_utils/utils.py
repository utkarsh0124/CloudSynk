from datetime import datetime, timedelta, timezone
import os
import random
import string

import re
#from urllib.parse import quote, unquote

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
    
class AzureBlobNameValidator:
    """Validates and sanitizes blob names according to Azure Storage rules"""
    
    # Azure blob naming constraints
    MIN_LENGTH = 1
    MAX_LENGTH = 1024
    
    # According to Azure docs: "A blob name can contain any combination of characters"
    # We only need to check length and avoid problematic endings
    # VALID_CHARS_PATTERN = r'^[a-zA-Z0-9\-_\.\/]+$'  # TOO RESTRICTIVE
    
    # Reserved/problematic patterns
    RESERVED_ENDINGS = ['.', '/', '\\']
    
    @classmethod
    def validate_blob_name(cls, blob_name: str) -> dict:
        """
        Validate a blob name against Azure Storage requirements
        
        Args:
            blob_name (str): The blob name to validate
            
        Returns:
            dict: {
                'is_valid': bool,
                'errors': list,
                'sanitized_name': str,
                'original_name': str
            }
        """
        errors = []
        sanitized = blob_name
        
        if not blob_name:
            return {
                'is_valid': False,
                'errors': ['Blob name cannot be empty'],
                'sanitized_name': 'unnamed_file',
                'original_name': blob_name
            }
        
        # Check length
        if len(blob_name) < cls.MIN_LENGTH:
            errors.append(f'Blob name must be at least {cls.MIN_LENGTH} character long')
        elif len(blob_name) > cls.MAX_LENGTH:
            errors.append(f'Blob name must be at most {cls.MAX_LENGTH} characters long')
            sanitized = sanitized[:cls.MAX_LENGTH]
        
        # Check for reserved endings
        for ending in cls.RESERVED_ENDINGS:
            if blob_name.endswith(ending):
                errors.append(f'Blob name cannot end with "{ending}"')
                sanitized = sanitized.rstrip(ending)
        
        # Azure allows any combination of characters, so we remove the restrictive character check
        # if not re.match(cls.VALID_CHARS_PATTERN, blob_name):
        #     errors.append('Blob name contains invalid characters')
        #     sanitized = cls._sanitize_name(sanitized)
        
        # Only sanitize if there are problematic endings
        if len(errors) > 0 and sanitized != blob_name:
            sanitized = cls._sanitize_name(sanitized)
        
        # Final validation of sanitized name
        if not sanitized:
            sanitized = 'unnamed_file'
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'sanitized_name': sanitized,
            'original_name': blob_name
        }
    
    @classmethod
    def _sanitize_name(cls, name: str) -> str:
        """
        Sanitize a blob name by removing problematic endings only
        Azure allows any combination of characters, so we keep this minimal
        
        Args:
            name (str): Name to sanitize
            
        Returns:
            str: Sanitized name
        """
        sanitized = name
        
        # Only remove problematic endings
        for ending in cls.RESERVED_ENDINGS:
            sanitized = sanitized.rstrip(ending)
        
        # If completely empty after sanitization, provide default
        return sanitized if sanitized else 'unnamed_file'
    
    @classmethod
    def sanitize_blob_name(cls, blob_name: str) -> str:
        """
        Quick sanitization method that returns a valid blob name
        
        Args:
            blob_name (str): Name to sanitize
            
        Returns:
            str: Valid Azure blob name
        """
        result = cls.validate_blob_name(blob_name)
        return result['sanitized_name']


def validate_azure_blob_name(blob_name: str) -> dict:
    """Convenience function for blob name validation"""
    return AzureBlobNameValidator.validate_blob_name(blob_name)


def sanitize_azure_blob_name(blob_name: str) -> str:
    """Convenience function for blob name sanitization"""
    return AzureBlobNameValidator.sanitize_blob_name(blob_name)