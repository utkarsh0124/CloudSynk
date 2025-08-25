from django.test import TestCase, Client
import json
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
        self.signup_url = reverse('signup')
        self.login_url = reverse('login')
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
        # Signup (API client -> JSON)
        resp = self.client.post(
            self.signup_url,
            json.dumps({
                'username': self.user_data['username'],
                'password1': self.user_data['password'],
                'password2': self.user_data['password'],
                'email_id': self.user_data['email_id']
            }),
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        # Fail fast with helpful output if signup didn't return JSON success
        if resp.status_code not in (200, 201):
            try:
                print('\n[DEBUG] signup response json:', resp.json())
            except Exception:
                print('\n[DEBUG] signup response content:', resp.content)
        self.assertIn(resp.status_code, (200, 201))

        # Fetch the created user and force-login so requests are authenticated
        user = User.objects.get(username=self.user_data['username'])
        self.client.force_login(user)
        # Ensure session keys exist after force_login
        self.assertIn('_auth_user_id', dict(self.client.session.items()))

        # Access home (API client expecting JSON)
        resp = self.client.get(self.home_url, HTTP_ACCEPT='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        if resp.status_code != 200:
            try:
                print('\n[DEBUG] home response json:', resp.json())
            except Exception:
                print('\n[DEBUG] home response content:', resp.content)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('blobs', data)
        self.assertEqual(data.get('username'), self.user_data['username'])

        # Logout
        resp = self.client.post(self.logout_url, HTTP_ACCEPT='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        if resp.status_code != 200:
            try:
                print('\n[DEBUG] logout response json:', resp.json())
            except Exception:
                print('\n[DEBUG] logout response content:', resp.content)
        self.assertEqual(resp.status_code, 200)

    def test_api_login_invalid(self):
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        resp = self.client.post(self.login_url, {'username': self.user_data['username'], 'password': 'wrong'})
        if resp.status_code == 200:
            try:
                print('\n[DEBUG] invalid login response json:', resp.json())
            except Exception:
                print('\n[DEBUG] invalid login response content:', resp.content)
        self.assertNotEqual(resp.status_code, 200)
        self.assertIn('error', resp.json())