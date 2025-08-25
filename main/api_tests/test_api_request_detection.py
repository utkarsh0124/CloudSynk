from django.test import TestCase, RequestFactory
from main import views


class ApiRequestDetectionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_accept_json(self):
        req = self.factory.get('/', HTTP_ACCEPT='application/json')
        self.assertTrue(views._is_api_request(req))

    def test_content_type_json(self):
        req = self.factory.post('/', content_type='application/json')
        self.assertTrue(views._is_api_request(req))

    def test_xhr_header(self):
        req = self.factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTrue(views._is_api_request(req))

    def test_html_request(self):
        req = self.factory.get('/', HTTP_ACCEPT='text/html')
        self.assertFalse(views._is_api_request(req))