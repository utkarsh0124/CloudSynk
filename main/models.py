from django.db import models
from django.contrib.auth.models import User
import hashlib
import time
from .subscription_config import SUBSCRIPTION_CHOICES, SUBSCRIPTION_VALUES


MAX_HASH_ID_FIELD_LENGTH = 12
MAX_BLOB_NAME_LENGTH = 1024
MAX_SHARING_LINK_LENGTH = 1024

class UserInfo(models.Model):
    MAX_CHOICES_LENGTH = 36
    
    #cannot have a custom PK like user_id as the django User model has a primary key
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True) # primary key
    user_name = models.CharField(max_length=100, null=False, blank=False)
    subscription_type = models.CharField(max_length=MAX_CHOICES_LENGTH, choices=SUBSCRIPTION_CHOICES, default="STARTER")
    container_name = models.CharField(max_length=250, default="None")
    storage_quota_bytes = models.BigIntegerField(null=False, default=0)  # 0 GB default quota
    storage_used_bytes = models.BigIntegerField(null=False, default=0)
    dob = models.DateField(null=True, blank=True)
    email_id = models.EmailField(max_length=254, null=True, blank=True)

class Blob(models.Model):
    blob_id = models.SlugField(max_length=MAX_HASH_ID_FIELD_LENGTH, unique=True, editable=False, null=False, blank=False) # primary key
    blob_name = models.CharField(max_length=MAX_BLOB_NAME_LENGTH, null=False, blank=False) # same blob names can exist for multiple users
    blob_size = models.BigIntegerField(null=False, blank=False, default=0)  # size in bytes
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False) # foreign key
    creation_time = models.FloatField(null=False, blank=True, default=time.time)
    last_modification_time = models.FloatField(null=False, blank=True, default=time.time)
    blob_type = models.CharField(max_length=50, null=False, blank=False, default="file")  # e.g., 'file', 'image', 'video'
    sharing_enabled = models.BooleanField(default=False)
    is_in_directory = models.BooleanField(default=False)
    directory_id = models.SlugField(max_length=32, null=True, blank=True) # foreign Key

    # Generate a hash based on timestamp and some unique data
    def save(self, *args, **kwargs):
        if not self.blob_id:
            unique_string = f"blob-{self.blob_name}-{time.time()}"
            self.blob_id = hashlib.md5(unique_string.encode()).hexdigest()[:MAX_HASH_ID_FIELD_LENGTH]
        super().save(*args, **kwargs)


class Sharing(models.Model):
    ACCESS_LEVEL_CHOICES = [
        ("READ", "Read"),
        ("WRITE", "Write")
    ]

    ACCESS_SCOPE_CHOICES = [
        ("USER", "User"),
        ("GROUP", "Group"),
        ("PUBLIC", "Public")
    ]
    
    MAX_CHOICES_LENGTH = 36

    object_id = models.SlugField(max_length=MAX_HASH_ID_FIELD_LENGTH, unique=True, editable=False, null=False, blank=False) # primary key
    global_access = models.BooleanField(default=False)
    access_level = models.CharField(max_length=MAX_CHOICES_LENGTH, choices=ACCESS_LEVEL_CHOICES, default="READ")
    access_scope = models.CharField(max_length=MAX_CHOICES_LENGTH, choices=ACCESS_SCOPE_CHOICES, default="USER")
    share_end_time = models.DateTimeField(null=True, blank=True)
    sharing_link = models.CharField(max_length=MAX_SHARING_LINK_LENGTH, null=True, blank=True)


class Directory(models.Model):
    directory_id = models.SlugField(max_length=MAX_HASH_ID_FIELD_LENGTH, unique=True, editable=False, null=False, blank=False) # primary key
    directory_name = models.CharField(max_length=MAX_BLOB_NAME_LENGTH, unique=True, editable=False, null=False, blank=False) # unique
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False) # foreign key
    creation_time = models.DateTimeField(null=False, blank=True)
    last_modification_time = models.DateTimeField(null=False, blank=True)
    parent_directory = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    is_sharing = models.BooleanField(default=False)

    # Generate a hash based on timestamp and some unique data
    def save(self, *args, **kwargs):
        if not self.directory_id:
            unique_string = f"directory-{self.directory_name}-{time.time()}"
            self.directory_id = hashlib.md5(unique_string.encode()).hexdigest()[:MAX_HASH_ID_FIELD_LENGTH]
        super().save(*args, **kwargs)