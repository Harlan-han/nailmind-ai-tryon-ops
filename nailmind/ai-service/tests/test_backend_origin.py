import unittest

from app import main


class BackendOriginTests(unittest.TestCase):
    def test_backend_origin_comes_from_webhook_url(self):
        origin = main.resolve_backend_origin("http://localhost:8114/api/tryon/webhook/result")

        self.assertEqual(origin, "http://localhost:8114")

    def test_relative_upload_urls_use_configured_backend_origin(self):
        original_origin = main.BACKEND_ORIGIN
        main.BACKEND_ORIGIN = "http://localhost:8114"
        try:
            self.assertEqual(
                main.to_backend_url("/uploads/hands/hand_01.jpg"),
                "http://localhost:8114/uploads/hands/hand_01.jpg",
            )
        finally:
            main.BACKEND_ORIGIN = original_origin

    def test_result_urls_use_configured_backend_origin(self):
        original_origin = main.BACKEND_ORIGIN
        main.BACKEND_ORIGIN = "http://localhost:8114"
        try:
            self.assertEqual(
                main.to_backend_upload_url("/uploads/results/result_1.jpg"),
                "http://localhost:8114/uploads/results/result_1.jpg",
            )
        finally:
            main.BACKEND_ORIGIN = original_origin


if __name__ == "__main__":
    unittest.main()
