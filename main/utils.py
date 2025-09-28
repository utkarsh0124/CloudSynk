"""
Utility functions for the main app
"""
import os
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from storage_webapp import logger, severity

def generate_and_store_avatar(username):
    """
    Generate an avatar from dicebear API and store it locally.
    
    Args:
        username (str): The username to generate avatar for
        
    Returns:
        str: The local path/URL to the stored avatar, or None if failed
    """
    try:
        # Generate avatar URL
        avatar_api_url = f"https://api.dicebear.com/9.x/initials/svg?seed={username}"
        
        # Download the avatar
        response = requests.get(avatar_api_url, timeout=10)
        response.raise_for_status()
        
        # Create avatar filename
        avatar_filename = f"avatars/{username}_avatar.svg"
        
        # Ensure the avatars directory exists
        avatar_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
        if not os.path.exists(avatar_dir):
            os.makedirs(avatar_dir, exist_ok=True)
        
        # Save the file using Django's default storage
        file_path = default_storage.save(avatar_filename, ContentFile(response.content))
        
        # Return the URL that can be used to access the file
        avatar_url = default_storage.url(file_path)
        
        logger.log(severity['INFO'], f"Avatar generated and stored for user {username}: {avatar_url}")
        return avatar_url
        
    except requests.exceptions.RequestException as e:
        logger.log(severity['ERROR'], f"Failed to download avatar for user {username}: {e}")
        return None
    except Exception as e:
        logger.log(severity['ERROR'], f"Failed to store avatar for user {username}: {e}")
        return None

def get_avatar_url(user_info):
    """
    Get the avatar URL for a user. Returns stored local avatar or falls back to external API.
    
    Args:
        user_info (UserInfo): The UserInfo instance
        
    Returns:
        str: The avatar URL to use
    """
    if user_info.avatar_url:
        # Check if local avatar file exists
        try:
            if hasattr(settings, 'MEDIA_ROOT') and user_info.avatar_url.startswith('/media/'):
                # Convert URL to file path
                file_path = os.path.join(settings.MEDIA_ROOT, user_info.avatar_url.replace('/media/', ''))
                if os.path.exists(file_path):
                    return user_info.avatar_url
        except Exception as e:
            logger.log(severity['WARNING'], f"Error checking local avatar for {user_info.user_name}: {e}")
    
    # Fallback to external API
    logger.log(severity['ERROR'], f"Failed to fetch avatar for user {user_info.user_name}, using fallback.")
    return f"https://api.dicebear.com/9.x/initials/svg?seed={user_info.user_name}"