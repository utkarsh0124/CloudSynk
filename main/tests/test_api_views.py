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


class APITests(TestCase):
    def setUp(self):
        self._orig_get_api = getattr(az_api, 'get_api_instance', None)
        az_api.get_api_instance = lambda *a, **k: _DummyAPI()

        self.client = Client()
        self.signup_url = reverse('auth_signup')
        self.login_url = reverse('auth_login')
        self.logout_url = reverse('logout')
        self.home_url = reverse('home')
        self.user_data = {
            'username': 'apitestuser',
            'password': 'testpassword123',
            'email_id': 'apitest@example.com',
            'email': 'apitest@example.com'
        }

    def tearDown(self):
        if self._orig_get_api is not None:
            az_api.get_api_instance = self._orig_get_api

    def test_api_signup_and_home_flow(self):
        # Signup
        resp = self.client.post(self.signup_url, {
            'username': self.user_data['username'],
            'password1': self.user_data['password'],
            'password2': self.user_data['password'],
            'email_id': self.user_data['email_id']
        })
        self.assertIn(resp.status_code, (200, 201))

        # Login
        resp = self.client.post(self.login_url, {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('success', False))

        # Access home
        resp = self.client.get(self.home_url)
        # should be forbidden unless logged in via session; client has session from login above
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('blobs', data)
        self.assertEqual(data.get('username'), self.user_data['username'])

        # Logout
        resp = self.client.post(self.logout_url)
        self.assertEqual(resp.status_code, 200)

    def test_api_login_invalid(self):
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        resp = self.client.post(self.login_url, {'username': self.user_data['username'], 'password': 'wrong'})
        self.assertNotEqual(resp.status_code, 200)
        self.assertIn('error', resp.json())
