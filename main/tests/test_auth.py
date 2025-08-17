from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
import json

class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_url = reverse('signup')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.user_data = {
            'username': 'testuser',
            'password': 'testpassword123',
            'email': 'testuser@example.com'
        }

    def test_signup_success(self):
        """Test successful user signup"""
        response = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password'],
            'email': self.user_data['email']
        })
        self.assertEqual(response.status_code, 200)  # Adjust based on your response
        self.assertTrue(User.objects.filter(username=self.user_data['username']).exists())

    def test_signup_duplicate_username(self):
        """Test signup with existing username"""
        User.objects.create_user(**self.user_data)
        response = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password'],
            'email': 'newemail@example.com'
        })
        self.assertNotEqual(response.status_code, 200)  # Expect failure
        self.assertIn('error', response.json())  # Adjust based on your error response

    def test_password_assertion(self):
        """Test password assertion during signup"""
        response = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password']+"_different_second_password",
            'email': self.user_data['email']
        })
        self.assertNotEqual(response.status_code, 200)  # Expect failure
        self.assertIn('error', response.json())  # Adjust based on your error response

    def test_login_success(self):
        """Test successful login"""
        User.objects.create_user(**self.user_data)
        response = self.client.post(self.login_url, {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('success', response.json())  # Adjust based on your success response

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        User.objects.create_user(**self.user_data)
        response = self.client.post(self.login_url, {
            'username': self.user_data['username'],
            'password': 'wrongpassword'
        })
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('error', response.json())  # Adjust based on your error response

    def test_logout(self):
        """Test successful logout"""
        User.objects.create_user(**self.user_data)
        self.client.login(**self.user_data)
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 200)
        # Verify user is logged out
        response = self.client.get(reverse('profile'))  # Adjust to a protected view
        self.assertNotEqual(response.status_code, 200)  # Should be redirected or unauthorized