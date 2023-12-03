from django.db import models
from django.contrib.auth.models import User

class Blob(models.Model):
    blob_name = models.CharField(primary_key=True, max_length=250, null=False, blank=False)
    blob_size = models.BigIntegerField(null=False, blank=False)
    container_name = models.CharField(max_length=250, null=False, blank=False)
    blob_update_time = models.DateTimeField(null=False, blank=True)

class UserInfo(models.Model):
    USER_CHOICES = (
        ("REGULAR", "Regular"),
        ("PREMIUM", "Premium")
    )
    
    user_type = models.CharField(max_length=10,choices=USER_CHOICES,default="REGULAR")
    container_id = models.CharField(max_length=200)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    storage_quota_kb = models.IntegerField()
    total_storage_size_kb = models.IntegerField()