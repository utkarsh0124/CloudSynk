"""
WSGI config for storage_webapp project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Force use of regular settings, not settings_prod
os.environ['DJANGO_SETTINGS_MODULE'] = 'storage_webapp.settings'
os.environ['SECURE_SSL_REDIRECT'] = 'false'

application = get_wsgi_application()
