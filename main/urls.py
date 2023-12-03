from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.home , name="home"),
    path("logout/", views.user_logout , name="logout"),
    path("login/", views.user_login, name="login"),
    path("auth_login/", views.login_auth , name="login"),
    path("signup/", views.user_signup , name="login"),
    path("auth_signup/", views.signup_auth , name="signup"),
    path("deleteFile/", views.delete_blob , name="logout"),
    path("addFile/", views.add_blob , name="logout"),
    path("", include("django.contrib.auth.urls")),
]