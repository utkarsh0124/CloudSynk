from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # path(regex_for_404, "media/error_404/error_404.html"),
    path("", include("main.urls")),
    path('admin/', admin.site.urls),
]
