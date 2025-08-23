from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserInfo


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email')

    def create(self, validated_data):
        username = validated_data['username']
        password = validated_data['password']
        email = validated_data.get('email')
        user = User.objects.create_user(username=username, password=password, email=email)
        return user


class UserInfoSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = UserInfo
        fields = ('user', 'container_name', 'subscription_type', 'storage_quota_bytes', 'storage_used_bytes', 'dob', 'email_id')
