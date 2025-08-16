from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.home , name="home"),
    path("logout/", views.user_logout , name="logout"),
    path("login/", views.user_login, name="login"),
    path("auth_login/", views.login_auth , name="auth_login"),
    path("signup/", views.user_signup , name="signup"),
    path("auth_signup/", views.signup_auth , name="auth_signup"),
    path("rmUser/", views.remove_user, name="user_remove"),
    path("deleteFile/<str:blob_name>/", views.delete_blob , name="delete"),
    path("addFile/", views.add_blob , name="add"),
    path("", include("django.contrib.auth.urls")),
]