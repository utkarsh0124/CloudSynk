from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('main.urls'))
]


# Only include admin in development
if settings.DEBUG:
    urlpatterns.append(path('admin/', admin.site.urls))
    # Serve media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)