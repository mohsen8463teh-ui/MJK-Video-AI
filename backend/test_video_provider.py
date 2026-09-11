import os
import sys
import unittest
BACKEND_DIR=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,BACKEND_DIR)
from video_provider import KIEProvider, RunwayProvider, VideoRouter
class VideoProviderTestCase(unittest.TestCase):
    def test_kie_safe_without_key(self):
        old=os.environ.pop("KIE_API_KEY4",None)
        try:
            p=KIEProvider(); self.assertFalse(p.configured); self.assertEqual(p.status()["id"],"kie")
        finally:
            if old is not None: os.environ["KIE_API_KEY4"]=old
    def test_router_prefers_kie(self):
        old=os.environ.get("KIE_API_KEY4")
        try:
            os.environ["KIE_API_KEY4"]="test-key"; self.assertEqual(VideoRouter().select().provider_id,"kie")
        finally:
            if old is None: os.environ.pop("KIE_API_KEY4",None)
            else: os.environ["KIE_API_KEY4"]=old
    def test_runway_safe_without_key(self):
        old=os.environ.pop("RUNWAYML_API_SECRET",None)
        try: self.assertFalse(RunwayProvider().configured)
        finally:
            if old is not None: os.environ["RUNWAYML_API_SECRET"]=old
if __name__=="__main__": unittest.main(verbosity=2)
