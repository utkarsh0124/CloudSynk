from django.urls import path
from . import views

urlpatterns = [
    path("", views.HomeAPIView.as_view(), name="home"),
    path("logout/", views.LogoutAPIView.as_view(), name="logout"),
    path("login/", views.LoginAPIView.as_view(), name="login"),
    path("auth_login/", views.LoginAPIView.as_view(), name="auth_login"),
    path("signup/", views.SignupAPIView.as_view(), name="signup"),
    path("auth_signup/", views.SignupAPIView.as_view(), name="auth_signup"),
    path("rmUser/", views.RemoveUserAPIView.as_view(), name="user_remove"),
    path("deleteFile/<str:blob_name>/", views.DeleteBlobAPIView.as_view(), name="delete"),
    path("addFile/", views.AddBlobAPIView.as_view(), name="add"),
    path("api/signup/", views.SignupAPIView.as_view(), name="api_signup"),
    path("api/login/", views.LoginAPIView.as_view(), name="api_login"),
    path("api/logout/", views.LogoutAPIView.as_view(), name="api_logout"),
]