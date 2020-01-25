from application import app
import unittest


class Test(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_health(self):
        response = self.app.get("/health")
        assert response.status == "200 OK"
        assert b"Healthy" in response.data
