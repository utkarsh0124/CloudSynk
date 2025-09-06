from urllib import response
from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth.models import User
from main.models import UserInfo

import az_intf.api as az_api

class AuthTests(TestCase):
    def setUp(self):
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

    def test_signup_success(self):
        """Test successful user signup (auth_signup)"""
        response = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password'],
            'email': self.user_data['email']
        }, format='json')
        if response.status_code not in (200, 201):
            try:
                print('\n[DEBUG] response json:', response.json())
            except Exception:
                print('\n[DEBUG] response content:', response.content) 
        self.assertIn(response.status_code, (200, 201))
        self.assertTrue(User.objects.filter(username=self.user_data['username']).exists())

    def test_signup_duplicate_username(self):
        """Signup should fail if username already exists"""
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        response = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password'],
            'email': 'newemail@example.com'
        }, format='json')
        if response.status_code not in (200, 201):
            try:
                print('\n[DEBUG] response json:', response.json())
            except Exception:
                print('\n[DEBUG] response content:', response.content)
        
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('error', response.json())

    def test_password_assertion(self):
        """Passwords mismatch should return JSON error"""
        response = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password'] + '_diff',
            'email': self.user_data['email']
        }, format='json')
        if response.status_code not in (200, 201):
            try:
                print('\n[DEBUG] response json:', response.json())
            except Exception:
                print('\n[DEBUG] response content:', response.content)
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('error', response.json())

    def test_login_success(self):
        """Valid credentials should return JSON success"""
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        response = self.client.post(self.login_url, {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        }, format='json')
        if response.status_code not in (200, 201):
            try:
                print('\n[DEBUG] response json:', response.json())
            except Exception:
                print('\n[DEBUG] response content:', response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('success', False))

    def test_login_invalid_credentials(self):
        """Wrong password returns JSON error"""
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        response = self.client.post(self.login_url, {
            'username': self.user_data['username'],
            'password': 'wrongpassword'
        }, format='json')
        if response.status_code not in (200, 201):
            try:
                print('\n[DEBUG] response json:', response.json())
            except Exception:
                print('\n[DEBUG] response content:', response.content)
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('error', response.json())

    def test_logout(self):
        """Logging out should end session and protect `home`"""
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        logged_in = self.client.login(username=self.user_data['username'], password=self.user_data['password'])
        self.assertTrue(logged_in)
        response = self.client.post(self.logout_url, format='json')
        if response.status_code not in (200, 201):
            try:
                print('\n[DEBUG] response json:', response.json())
            except Exception:
                print('\n[DEBUG] response content:', response.content)
        self.assertIn(response.status_code, (200, 302))
        resp_after = self.client.get(reverse('home'))
        if resp_after.status_code not in (200, 201):
            try:
                print('\n[DEBUG] response json:', resp_after.json())
            except Exception:
                print('\n[DEBUG] response content:', resp_after.content)
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
        if resp.status_code not in (200, 201):
            try:
                print('\n[DEBUG] response json:', resp.json())
            except Exception:
                print('\n[DEBUG] response content:', resp.content)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get('success', False))

        # with the same client (session cookie), access home
        resp2 = self.client.get(reverse('home'))
        if resp2.status_code not in (200, 201):
            try:
                print('\n[DEBUG] response json:', resp2.json())
            except Exception:
                print('\n[DEBUG] response content:', resp2.content)
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
            'email': self.user_data['email']
        }, format='json')
        if response.status_code not in (200, 201):
            try:
                print('\n[DEBUG] response json:', response.json())
            except Exception:
                print('\n[DEBUG] response content:', response.content)
        self.assertIn(response.status_code, (200, 201))
        self.assertTrue(User.objects.filter(username=self.user_data['username']).exists())

        logged_in = self.client.login(username=self.user_data['username'], password=self.user_data['password'])
        self.assertTrue(logged_in)

        # Deactivate (delete) the user
        deactivate_url = reverse('deactivate')
        response = self.client.post(deactivate_url, follow=True)
        if response.status_code not in (200, 201):
            try:
                print('\n[DEBUG] response json:', response.json())
            except Exception:
                print('\n[DEBUG] response content:', response.content)
        self.assertIn(response.status_code, (200, 302))
        self.assertFalse(User.objects.filter(username=self.user_data['username']).exists())

        # Try to login again (should fail)
        login_response = self.client.post(self.login_url, {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        }, format='json')
        if login_response.status_code not in (200, 201):
            try:
                print('\n[DEBUG] response json:', login_response.json())
            except Exception:
                print('\n[DEBUG] response content:', login_response.content)
        self.assertNotEqual(login_response.status_code, 200)
        self.assertIn('error', login_response.json())