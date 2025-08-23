from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

import az_intf.api as az_api


class _DummyAPI:
    def add_container(self, user):
        return True

    def create_blob(self, name):
        return True

    def delete_blob(self, name):
        return True

    def list_blob(self):
        return []

    def get_blob_size(self, name):
        return 0


class AuthTests(TestCase):
    def setUp(self):
        # Patch external API to avoid real Azure calls during tests
        self._orig_get_api = getattr(az_api, 'get_api_instance', None)
        az_api.get_api_instance = lambda *a, **k: _DummyAPI()

        self.client = Client()
        self.signup_url = reverse('auth_signup')
        self.login_url = reverse('auth_login')
        self.logout_url = reverse('logout')
        self.user_data = {
            'username': 'testuser',
            'password': 'testpassword123',
            'email_id': 'testuser@example.com',
            'email': 'testuser@example.com'
        }

    def tearDown(self):
        # Restore patched API function
        if self._orig_get_api is not None:
            az_api.get_api_instance = self._orig_get_api

    def test_signup_success(self):
        """Test successful user signup (auth_signup)"""
        response = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password'],
            'email_id': self.user_data['email_id']
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username=self.user_data['username']).exists())

    def test_signup_duplicate_username(self):
        """Signup should fail if username already exists"""
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        response = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password'],
            'email_id': 'newemail@example.com'
        })
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('error', response.json())

    def test_password_assertion(self):
        """Passwords mismatch should return JSON error"""
        response = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password'] + '_diff',
            'email_id': self.user_data['email_id']
        })
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('error', response.json())

    def test_login_success(self):
        """Valid credentials should return JSON success"""
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        response = self.client.post(self.login_url, {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('success', False))

    def test_login_invalid_credentials(self):
        """Wrong password returns JSON error"""
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        response = self.client.post(self.login_url, {
            'username': self.user_data['username'],
            'password': 'wrongpassword'
        })
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('error', response.json())

    def test_logout(self):
        """Logging out should end session and protect `home`"""
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        logged_in = self.client.login(username=self.user_data['username'], password=self.user_data['password'])
        self.assertTrue(logged_in)
        response = self.client.post(self.logout_url, follow=True)
        self.assertIn(response.status_code, (200, 302))
        resp_after = self.client.get(reverse('home'))
        self.assertNotEqual(resp_after.status_code, 200)