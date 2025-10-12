from django.urls import path
from . import views

urlpatterns = [
    path("", views.HomeAPIView.as_view(), name="home"),
    path("home/", views.HomeAPIView.as_view(), name="home"),
    path("signup/", views.SignupAPIView.as_view(), name="signup"),
    path("login/", views.LoginAPIView.as_view(), name="login"),
    path("logout/", views.LogoutAPIView.as_view(), name="logout"),
    path("deactivate/", views.DeactivateUserAPIView.as_view(), name="deactivate"),
    path("deleteFile/<str:blob_id>/", views.DeleteBlobAPIView.as_view(), name="delete"),
    path("downloadFile/<str:blob_id>/", views.DownloadBlobAPIView.as_view(), name="download"),
    path("chunkedUpload/", views.ChunkedUploadAPIView.as_view(), name="chunked_upload"),
    path("cancelDownload/<str:blob_id>/", views.CancelDownloadAPIView.as_view(), name="cancel_download"),
    path("activeUploads/", views.ActiveUploadsAPIView.as_view(), name="active_uploads"),
    path("signup/verify-otp/", views.OTPVerifyAPIView.as_view(), name="verify_otp"),
    path("signup/resend-otp/", views.ResendOTPAPIView.as_view(), name="resend_otp"),
    
    # Admin URLs
    path("admin/users/", views.AdminUserListAPIView.as_view(), name="admin_users"),
    path("admin/users/<int:user_id>/delete/", views.AdminDeleteUserAPIView.as_view(), name="admin_delete_user"),
    path("admin/users/<int:user_id>/subscription/", views.AdminUpdateUserSubscriptionAPIView.as_view(), name="admin_update_subscription"),
]