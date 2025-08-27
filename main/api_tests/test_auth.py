from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth.models import User
from main.models import UserInfo

import az_intf.api as az_api


class _DummyAPI:
    def delete_container(self):
        return True
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

        self.client = APIClient()
        self.signup_url = reverse('signup')
        self.login_url = reverse('login')
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
        }, format='json')
        self.assertIn(response.status_code, (200, 201))
        self.assertTrue(User.objects.filter(username=self.user_data['username']).exists())

    def test_signup_duplicate_username(self):
        """Signup should fail if username already exists"""
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        response = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password'],
            'email_id': 'newemail@example.com'
        }, format='json')
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('error', response.json())

    def test_password_assertion(self):
        """Passwords mismatch should return JSON error"""
        response = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password'] + '_diff',
            'email_id': self.user_data['email_id']
        }, format='json')
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('error', response.json())

    def test_login_success(self):
        """Valid credentials should return JSON success"""
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        response = self.client.post(self.login_url, {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('success', False))

    def test_login_invalid_credentials(self):
        """Wrong password returns JSON error"""
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        response = self.client.post(self.login_url, {
            'username': self.user_data['username'],
            'password': 'wrongpassword'
        }, format='json')
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('error', response.json())

    def test_logout(self):
        """Logging out should end session and protect `home`"""
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        logged_in = self.client.login(username=self.user_data['username'], password=self.user_data['password'])
        self.assertTrue(logged_in)
        response = self.client.post(self.logout_url, format='json')
        self.assertIn(response.status_code, (200, 302))
        resp_after = self.client.get(reverse('home'))
        self.assertNotEqual(resp_after.status_code, 200)

    def test_session_access_home(self):
        """Login via POST creates session; session can be used to access protected `home`"""
        user = User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        # create associated UserInfo so HomeAPIView can find container_name and quotas
        UserInfo.objects.create(
            user=user,
            user_name=self.user_data['username'],
            subscription_type='STARTER',
            container_name='test-container',
            storage_quota_bytes=1024 * 1024,
            storage_used_bytes=0,
            email_id=self.user_data['email']
        )
        # login via API (POST); API should return JSON success and set session cookie
        resp = self.client.post(self.login_url, {'username': self.user_data['username'], 'password': self.user_data['password']}, format='json')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get('success', False))

        # with the same client (session cookie), access home
        resp2 = self.client.get(reverse('home'))
        self.assertEqual(resp2.status_code, 200)
        data = resp2.json() if resp2['Content-Type'].startswith('application/json') else {}
        # Home view should indicate success for authenticated session
        # If it returned HTML, ensure the authenticated user is served the page (status 200)
        self.assertIn(resp2.status_code, (200,))

    def test_deactivate_user(self):
        """Test user deactivation (deletion) via the deactivate endpoint"""
        # Signup and login
        response = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password'],
            'email_id': self.user_data['email_id']
        }, format='json')
        self.assertIn(response.status_code, (200, 201))
        self.assertTrue(User.objects.filter(username=self.user_data['username']).exists())

        logged_in = self.client.login(username=self.user_data['username'], password=self.user_data['password'])
        self.assertTrue(logged_in)

        # Deactivate (delete) the user
        deactivate_url = reverse('deactivate')
        response = self.client.post(deactivate_url, follow=True)
        self.assertIn(response.status_code, (200, 302))
        self.assertFalse(User.objects.filter(username=self.user_data['username']).exists())

        # Try to login again (should fail)
        login_response = self.client.post(self.login_url, {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        }, format='json')
        self.assertNotEqual(login_response.status_code, 200)
        self.assertIn('error', login_response.json())