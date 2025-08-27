from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.SignupAPIView.as_view(), name='api_signup'),
    path('login/', views.LoginAPIView.as_view(), name='api_login'),
    path('logout/', views.LogoutAPIView.as_view(), name='api_logout'),
    path("deactivate/", views.DeactivateUserAPIView.as_view(), name="deactivate"),
    path('deleteFile/<str:blob_name>/', views.DeleteBlobAPIView.as_view(), name='api_delete'),
    path('addFile/', views.AddBlobAPIView.as_view(), name='api_add'),
]
