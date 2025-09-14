from django.urls import path, include
from django.conf import settings
from . import views

urlpatterns = [
    path("", views.HomeAPIView.as_view(), name="home"),
    path("home/", views.HomeAPIView.as_view(), name="home"),
    path("signup/", views.SignupAPIView.as_view(), name="signup"),
    path("login/", views.LoginAPIView.as_view(), name="login"),
    path("logout/", views.LogoutAPIView.as_view(), name="logout"),
    path("deactivate/", views.DeactivateUserAPIView.as_view(), name="deactivate"),
    path("deleteFile/<str:blob_id>/", views.DeleteBlobAPIView.as_view(), name="delete"),
    path("addFile/", views.AddBlobAPIView.as_view(), name="add"),
    path("downloadFile/<str:blob_id>/", views.DownloadBlobAPIView.as_view(), name="download"),
    # path("chunkedUpload/", views.ChunkedUploadAPIView.as_view(), name="chunked_upload"),
]

# Conditionally include API-only endpoints. This keeps production URL space free of
# API routes unless explicitly enabled via settings.ENABLE_API_ENDPOINTS or during
# DEBUG/tests (safe defaults for development).
def _api_enabled():
    explicit = getattr(settings, 'ENABLE_API_ENDPOINTS', None)
    if explicit is not None:
        return bool(explicit)
    if getattr(settings, 'DEBUG', False):
        return True
    import sys
    if any('test' in a for a in sys.argv):
        return True
    return False

if _api_enabled():
    urlpatterns += [
        path('api/', include('main.api_urls')),
    ]