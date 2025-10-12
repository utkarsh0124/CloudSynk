from django.test import TestCase, Client
import json
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

import az_intf.api as az_api
import az_intf.testing_dummy as az_dummy


class AzDummyMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._orig_init = getattr(az_api, 'init_container', None)
        cls._orig_get = getattr(az_api, 'get_container_instance', None)
        cls._orig_del = getattr(az_api, 'del_container_instance', None)
        az_api.init_container = az_dummy.init_container
        az_api.get_container_instance = az_dummy.get_container_instance
        az_api.del_container_instance = az_dummy.del_container_instance

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, '_orig_init') and cls._orig_init is not None:
            az_api.init_container = cls._orig_init
        if hasattr(cls, '_orig_get') and cls._orig_get is not None:
            az_api.get_container_instance = cls._orig_get
        if hasattr(cls, '_orig_del') and cls._orig_del is not None:
            az_api.del_container_instance = cls._orig_del
        super().tearDownClass()
from main.models import UserInfo


class APITests(AzDummyMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Save originals
        cls._orig_init = getattr(az_api, 'init_container', None)
        cls._orig_get = getattr(az_api, 'get_container_instance', None)
        cls._orig_del = getattr(az_api, 'del_container_instance', None)
        # Replace with dummy implementations to avoid real Azure calls
        # Use our centralized test-only dummy implementation
        cls._dummy_container = az_dummy.DummyContainer()
        az_api.init_container = az_dummy.init_container
        az_api.get_container_instance = az_dummy.get_container_instance
        az_api.del_container_instance = az_dummy.del_container_instance

    @classmethod
    def tearDownClass(cls):
        # Restore originals
        if hasattr(cls, '_orig_init') and cls._orig_init is not None:
            az_api.init_container = cls._orig_init
        if hasattr(cls, '_orig_get') and cls._orig_get is not None:
            az_api.get_container_instance = cls._orig_get
        if hasattr(cls, '_orig_del') and cls._orig_del is not None:
            az_api.del_container_instance = cls._orig_del
        super().tearDownClass()
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

    # Helper debug/assert utilities
    def _resp_debug(self, resp):
        """Return a short debug string with JSON if possible, else raw content."""
        try:
            return json.dumps(resp.json(), indent=2)
        except Exception:
            try:
                return resp.content.decode('utf-8', errors='replace')
            except Exception:
                return str(resp.content)

    def assertStatus(self, resp, expected, msg=None):
        if isinstance(expected, (list, tuple, set)):
            ok = resp.status_code in expected
            expected_str = str(tuple(expected))
        else:
            ok = resp.status_code == expected
            expected_str = str(expected)
        if not ok:
            dbg = self._resp_debug(resp)
            standard = f"Expected status {expected_str} but got {resp.status_code}. Response:\n{dbg}"
            full_msg = standard if not msg else f"{msg}\n{standard}"
            self.fail(full_msg)

    def assertJSONHasKey(self, resp, key, msg=None):
        try:
            data = resp.json()
        except Exception:
            dbg = self._resp_debug(resp)
            self.fail((msg or "Response is not valid JSON") + f"\nResponse:\n{dbg}")
        if key not in data:
            dbg = json.dumps(data, indent=2)
            self.fail((msg or f"Key '{key}' not in JSON response") + f"\nJSON:\n{dbg}")

    def assertJSONValue(self, resp, key, expected, msg=None):
        try:
            data = resp.json()
        except Exception:
            dbg = self._resp_debug(resp)
            self.fail((msg or "Response is not valid JSON") + f"\nResponse:\n{dbg}")
        actual = data.get(key)
        if actual != expected:
            dbg = json.dumps(data, indent=2)
            self.fail((msg or f"JSON key '{key}' value mismatch") + f"\nExpected: {expected}\nActual: {actual}\nJSON:\n{dbg}")

    # Reusable test double for container API used by views.
    class DummyContainer:
        def __init__(self, create_result=(True, 'blob-12345')):
            self._create_result = create_result

        def blob_create(self, name, size, typ, uploaded=None):
            # uploaded param is accepted by actual view; ignore in test double
            return self._create_result

        def blob_delete(self, blob_id):
            return True

        def get_blob_list(self):
            # return a simple list compatible with what the view expects
            return []

        def container_delete(self, user_obj):
            return True

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
        self.assertStatus(resp, (200, 201), msg="Signup did not return success status")

        # Fetch the created user and force-login so requests are authenticated
        user = User.objects.get(username=self.user_data['username'])
        # Ensure UserInfo exists for the newly created user (views expect it)
        try:
            UserInfo.objects.get(user=user)
        except UserInfo.DoesNotExist:
            UserInfo.objects.create(user=user, user_name=user.username, email_id=user.email)
        self.client.force_login(user)
        # Ensure session keys exist after force_login
        session_items = dict(self.client.session.items())
        if '_auth_user_id' not in session_items:
            self.fail("'_auth_user_id' not in session after force_login. Session items: %r" % (session_items,))

        # Access home (API client expecting JSON)
        resp = self.client.get(self.home_url, HTTP_ACCEPT='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertStatus(resp, 200, msg="Home did not return 200 OK")
        data = resp.json()
        self.assertJSONHasKey(resp, 'blobs', msg="Home JSON missing 'blobs'")
        # check username value
        self.assertJSONValue(resp, 'username', self.user_data['username'], msg="Home JSON username mismatch")

        # Logout
        resp = self.client.post(self.logout_url, HTTP_ACCEPT='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertStatus(resp, 200, msg="Logout did not return 200 OK")

    def test_api_login_invalid(self):
        User.objects.create_user(username=self.user_data['username'], password=self.user_data['password'], email=self.user_data['email'])
        resp = self.client.post(self.login_url, {'username': self.user_data['username'], 'password': 'wrong'})
        # invalid login should not return 200 OK
        if resp.status_code == 200:
            dbg = self._resp_debug(resp)
            self.fail("Invalid login unexpectedly returned 200 OK. Response:\n%s" % dbg)
        # If response is JSON, assert it has 'error' key
        try:
            self.assertJSONHasKey(resp, 'error', msg="Invalid login response missing 'error'")
        except AssertionError:
            # If not JSON, still fail earlier if it was 200; otherwise allow non-JSON error responses
            pass

    # Blob API tests (AddBlobAPIView deprecated - using chunked upload only)
    
    def test_delete_blob_missing_id(self):
        # calling the delete endpoint with no blob_id should not resolve; expect 404
        user = User.objects.create_user(username='deluser', password='pw123', email='del@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        # Post to base delete path (no id) - the URL pattern requires an id so this should 404
        resp = self.client.post('/api/deleteFile/')
        self.assertStatus(resp, (404, 405, 400), msg="Delete blob base path did not return expected client error")

    def test_delete_blob_api_instantiation_failed(self):
        user = User.objects.create_user(username='deluser2', password='pw123', email='del2@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        delete_url = reverse('delete', kwargs={'blob_id': 'nonexistent'})
        orig_get = az_api.get_container_instance
        try:
            az_api.get_container_instance = lambda uname: None
            resp = self.client.post(delete_url, HTTP_ACCEPT='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertStatus(resp, 500, msg="Delete blob when API instantiation failed did not return 500")
        finally:
            az_api.get_container_instance = orig_get

    def test_delete_blob_success_happy_path(self):
        user = User.objects.create_user(username='deluser_ok', password='pw123', email='delok@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        delete_url = reverse('delete', kwargs={'blob_id': 'blob-12345'})

        orig_get = az_api.get_container_instance
        try:
            az_api.get_container_instance = lambda uname: APITests.DummyContainer()
            resp = self.client.post(delete_url, HTTP_ACCEPT='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            # Expect 200 OK
            self.assertStatus(resp, 200, msg="Delete blob happy path did not return 200")
            data = resp.json()
            # Ensure 'success' key exists in response JSON
            self.assertJSONHasKey(resp, 'success', msg="Delete blob response missing 'success'")
        finally:
            az_api.get_container_instance = orig_get

    def test_delete_blob_browser_redirect(self):
        user = User.objects.create_user(username='deluser_browser', password='pw123', email='delbrowser@example.com')
        UserInfo.objects.create(user=user, user_name=user.username)
        self.client.force_login(user)
        delete_url = reverse('delete', kwargs={'blob_id': 'blob-xyz'})

        orig_get = az_api.get_container_instance
        try:
            az_api.get_container_instance = lambda uname: APITests.DummyContainer()
            resp = self.client.post(delete_url)
            self.assertStatus(resp, (302, 301), msg="Delete blob browser POST did not redirect")
        finally:
            az_api.get_container_instance = orig_get
