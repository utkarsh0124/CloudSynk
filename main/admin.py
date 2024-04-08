from django.contrib import admin
from .models import UserInfo, Blob

admin.site.register(Blob)
admin.site.register(UserInfo)