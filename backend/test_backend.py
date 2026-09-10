import os
import sys
import unittest

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

from main import app


class BackendAPITestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True)
        cls.client = app.test_client()

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])

    def test_models(self):
        r = self.client.get("/v1/models")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])

    def test_director_create(self):
        r = self.client.post(
            "/v1/director/create",
            json={
                "prompt": "یک تبلیغ ۳۰ ثانیه‌ای برای فروشگاه عینک",
                "output_type": "تبلیغ مغازه",
                "style": "cinematic",
                "duration_seconds": 30,
                "language": "فارسی",
                "aspect_ratio": "9:16"
            }
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(
            data["plan"]["director"]["aspect_ratio"],
            "9:16"
        )

    def test_project_plan(self):
        r = self.client.post(
            "/v1/projects/plan",
            json={"prompt": "یک ویدیوی سینمایی درباره شهر آینده"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])

    def test_llm_status(self):
        r = self.client.get("/v1/llm/status")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("provider_available", data["status"])

    def test_llm_director_request(self):
        r = self.client.post(
            "/v1/llm/director-request",
            json={
                "prompt": "یک تبلیغ حرفه‌ای برای یک محصول جدید",
                "duration_seconds": 30,
                "style": "cinematic",
                "language": "فارسی",
                "aspect_ratio": "9:16",
                "output_type": "advertising"
            }
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("system_instruction", data["request"])
        self.assertIn("user_request", data["request"])
        self.assertIn("response_schema", data["request"])

    def test_empty_prompt_rejected(self):
        r = self.client.post(
            "/v1/llm/director-request",
            json={"prompt": ""}
        )
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
