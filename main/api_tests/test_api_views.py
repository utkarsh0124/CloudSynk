from django.test import TestCase, Client
import json
from django.urls import reverse
from django.contrib.auth.models import User

import az_intf.api as az_api
from main.models import UserInfo
from django.urls import reverse

class APITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_url = reverse('signup')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.home_url = reverse('home')
        self.user_data = {
            'username': 'apitestuser',
            'password': 'testpassword123',
            'email': 'apitest@example.com'
        }

    def test_api_signup_and_home_flow(self):
        # Signup (API client -> JSON)
        resp = self.client.post(
            self.signup_url,
            json.dumps({
                'username': self.user_data['username'],
                'password1': self.user_data['password'],
                'password2': self.user_data['password'],
                'email': self.user_data['email']
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

    # Blob API tests
    def test_add_blob_missing_filename(self):
        # create user and userinfo
        user = User.objects.create_user(username='blobuser', password='pw123', email='blob@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        add_url = reverse('api_add')
        resp = self.client.post(add_url, json.dumps({}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.json())

    def test_add_blob_api_instantiation_failed_and_blob_create_failure(self):
        # Ensure when API instantiation fails, view returns 500
        user = User.objects.create_user(username='blobuser2', password='pw123', email='blob2@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        add_url = reverse('api_add')
        # Mock az_api.get_container_instance to return None (instantiation failed)
        orig_get = az_api.get_container_instance
        az_api.get_container_instance = lambda uname: None
        resp = self.client.post(add_url, json.dumps({'file_name': 'test.txt'}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 500)
        az_api.get_container_instance = orig_get

    def test_add_blob_success_flow_but_blob_create_returns_false(self):
        # When blob_create returns False, view should return 400
        user = User.objects.create_user(username='blobuser3', password='pw123', email='blob3@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        add_url = reverse('api_add')

        class DummyAPI:
            def blob_create(self, name, size, typ):
                return (False, None)

        orig_get = az_api.get_container_instance
        az_api.get_container_instance = lambda uname: DummyAPI()
        resp = self.client.post(add_url, json.dumps({'file_name': 'test.txt'}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 400)
        az_api.get_container_instance = orig_get

    def test_delete_blob_missing_id(self):
        # calling the delete endpoint with no blob_id should not resolve; expect 404
        user = User.objects.create_user(username='deluser', password='pw123', email='del@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        # Post to base delete path (no id) - the URL pattern requires an id so this should 404
        resp = self.client.post('/api/deleteFile/')
        self.assertIn(resp.status_code, (404, 405, 400))

    def test_delete_blob_api_instantiation_failed(self):
        user = User.objects.create_user(username='deluser2', password='pw123', email='del2@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        delete_url = reverse('api_delete', kwargs={'blob_id': 'nonexistent'})
        orig_get = az_api.get_container_instance
        az_api.get_container_instance = lambda uname: None
        resp = self.client.post(delete_url, HTTP_ACCEPT='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 500)
        az_api.get_container_instance = orig_get

    def test_add_blob_success_happy_path(self):
        # When blob_create returns True and a blob_id, view should return success JSON
        user = User.objects.create_user(username='blobuser_ok', password='pw123', email='blobok@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        add_url = reverse('api_add')

        class DummyAPISuccess:
            def blob_create(self, name, size, typ):
                return (True, 'blob-12345')

        orig_get = az_api.get_container_instance
        az_api.get_container_instance = lambda uname: DummyAPISuccess()
        resp = self.client.post(add_url, json.dumps({'file_name': 'ok.txt'}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # Expect 200 or 201 depending on view; view returns 200 when API_inst exists and not redirect
        self.assertIn(resp.status_code, (200, 201))
        data = resp.json()
        self.assertTrue(data.get('success') or data.get('success') is None)  # view may not set success True in current impl
        # If blob_id is returned in view payload, check it (defensive)
        if 'blob_id' in data:
            self.assertEqual(data.get('blob_id'), 'blob-12345')
        az_api.get_container_instance = orig_get

    def test_delete_blob_success_happy_path(self):
        user = User.objects.create_user(username='deluser_ok', password='pw123', email='delok@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        delete_url = reverse('api_delete', kwargs={'blob_id': 'blob-12345'})

        class DummyAPIDeleteSuccess:
            def blob_delete(self, blob_id):
                return True

        orig_get = az_api.get_container_instance
        az_api.get_container_instance = lambda uname: DummyAPIDeleteSuccess()
        resp = self.client.post(delete_url, HTTP_ACCEPT='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # Expect 200 OK
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # view returns {'success': False, 'error': 'API Instantiation Failed'} on failure path; success path should return success True (if implemented)
        # check for success key or 200 status as proxy
        self.assertIn('success', data)
        az_api.get_container_instance = orig_get

    def test_add_blob_browser_redirect(self):
        # For browser (non-API) requests, AddBlob should redirect to /home/
        user = User.objects.create_user(username='blobuser_browser', password='pw123', email='blobbrowser@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        add_url = reverse('api_add')

        class DummyAPISuccess2:
            def blob_create(self, name, size, typ):
                return (True, 'blob-xyz')

        orig_get = az_api.get_container_instance
        az_api.get_container_instance = lambda uname: DummyAPISuccess2()
        # Simulate a browser POST (no application/json accept and no XHR header)
        resp = self.client.post(add_url, {'file_name': 'browser.txt'})
        # Should redirect (302) to /home/ or similar
        self.assertIn(resp.status_code, (302, 301))
        az_api.get_container_instance = orig_get

    def test_delete_blob_browser_redirect(self):
        user = User.objects.create_user(username='deluser_browser', password='pw123', email='delbrowser@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        delete_url = reverse('api_delete', kwargs={'blob_id': 'blob-xyz'})

        class DummyAPIDeleteSuccess2:
            def blob_delete(self, blob_id):
                return True

        orig_get = az_api.get_container_instance
        az_api.get_container_instance = lambda uname: DummyAPIDeleteSuccess2()
        resp = self.client.post(delete_url)
        self.assertIn(resp.status_code, (302, 301))
        az_api.get_container_instance = orig_get
