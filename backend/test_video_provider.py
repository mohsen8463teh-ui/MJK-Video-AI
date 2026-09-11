import os
import sys
import unittest

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

from video_provider import RunwayProvider, VideoRouter


class VideoProviderTestCase(unittest.TestCase):

    def test_unconfigured_provider_is_safe(self):
        old = os.environ.pop("RUNWAYML_API_SECRET", None)
        try:
            provider = RunwayProvider()
            self.assertFalse(provider.configured)
            self.assertEqual(provider.status()["id"], "runway")
        finally:
            if old is not None:
                os.environ["RUNWAYML_API_SECRET"] = old

    def test_router_status(self):
        status = VideoRouter().status()
        self.assertIn("provider_available", status)
        self.assertEqual(status["providers"][0]["id"], "runway")


if __name__ == "__main__":
    unittest.main(verbosity=2)
