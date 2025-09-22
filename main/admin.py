from django.contrib import admin
from django.contrib.auth.models import User
from .models import UserInfo, Blob, Directory, Sharing
from .subscription_config import SUBSCRIPTION_VALUES
from storage_webapp import logger, severity


class UserInfoAdmin(admin.ModelAdmin):
    """
    Custom admin interface for UserInfo model.
    Automatically updates storage quota based on subscription type.
    """
    list_display = ('user', 'user_name', 'subscription_type', 'storage_quota_gb', 'storage_used_gb', 'email_id')
    list_filter = ('subscription_type',)
    search_fields = ('user__username', 'user_name', 'email_id')
    readonly_fields = ('storage_quota_bytes', 'storage_used_bytes', 'container_name')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_name', 'email_id', 'dob')
        }),
        ('Subscription & Storage', {
            'fields': ('subscription_type', 'storage_quota_bytes', 'storage_used_bytes'),
            'description': 'Storage quota is automatically updated based on subscription type.'
        }),
        ('System Information', {
            'fields': ('container_name',),
            'classes': ('collapse',)
        }),
    )
    
    def storage_quota_gb(self, obj):
        """Display storage quota in GB for better readability"""
        return f"{obj.storage_quota_bytes / (1024**3):.2f} GB"
    storage_quota_gb.short_description = 'Storage Quota'
    
    def storage_used_gb(self, obj):
        """Display storage used in GB for better readability"""
        return f"{obj.storage_used_bytes / (1024**3):.2f} GB"
    storage_used_gb.short_description = 'Storage Used'
    
    def save_model(self, request, obj, form, change):
        """
        Override save to automatically update storage quota based on subscription type
        """
        # Get the new subscription type
        new_subscription = obj.subscription_type
        
        # Update storage quota based on subscription config
        if new_subscription in SUBSCRIPTION_VALUES:
            old_quota = obj.storage_quota_bytes
            new_quota = SUBSCRIPTION_VALUES[new_subscription]
            obj.storage_quota_bytes = new_quota
            
            # Log the change for audit purposes
            if change and old_quota != new_quota:
                logger.log(
                    severity['INFO'], 
                    f"Admin {request.user.username} updated user {obj.user.username} "
                    f"subscription from quota {old_quota} to {new_quota} bytes "
                    f"(subscription: {new_subscription})"
                )
                
                # Add a message to show the admin what happened
                from django.contrib import messages
                messages.success(
                    request, 
                    f"Storage quota automatically updated to {new_quota / (1024**3):.2f} GB "
                    f"based on {new_subscription} subscription."
                )
        
        super().save_model(request, obj, form, change)


class BlobAdmin(admin.ModelAdmin):
    """
    Custom admin interface for Blob model with better display and filtering
    """
    list_display = ('blob_name', 'user_id', 'blob_size_mb', 'blob_type', 'sharing_enabled', 'creation_time')
    list_filter = ('blob_type', 'sharing_enabled', 'user_id')
    search_fields = ('blob_name', 'user_id__username')
    readonly_fields = ('blob_id', 'creation_time', 'last_modification_time')
    
    def blob_size_mb(self, obj):
        """Display blob size in MB for better readability"""
        return f"{obj.blob_size / (1024**2):.2f} MB"
    blob_size_mb.short_description = 'File Size'


class DirectoryAdmin(admin.ModelAdmin):
    """
    Custom admin interface for Directory model
    """
    list_display = ('directory_name', 'user_id', 'parent_directory', 'is_sharing', 'creation_time')
    list_filter = ('is_sharing', 'user_id')
    search_fields = ('directory_name', 'user_id__username')
    readonly_fields = ('directory_id', 'creation_time', 'last_modification_time')


class SharingAdmin(admin.ModelAdmin):
    """
    Custom admin interface for Sharing model
    """
    list_display = ('object_id', 'access_level', 'access_scope', 'global_access', 'share_end_time')
    list_filter = ('access_level', 'access_scope', 'global_access')
    readonly_fields = ('object_id',)


# Register models with custom admin classes
admin.site.register(UserInfo, UserInfoAdmin)
admin.site.register(Blob, BlobAdmin)
admin.site.register(Directory, DirectoryAdmin)
admin.site.register(Sharing, SharingAdmin)

# Customize admin site headers
admin.site.site_header = "CloudSynk Administration"
admin.site.site_title = "CloudSynk Admin"
admin.site.index_title = "CloudSynk Management Portal"