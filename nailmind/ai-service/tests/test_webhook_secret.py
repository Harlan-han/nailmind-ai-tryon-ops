import unittest
from unittest.mock import AsyncMock, patch

from app import main


class NotifyBackendResultTests(unittest.IsolatedAsyncioTestCase):
    async def test_notify_backend_result_uses_backend_webhook_secret_header(self):
        original_secret = main.BACKEND_WEBHOOK_SECRET
        main.BACKEND_WEBHOOK_SECRET = "backend-secret"
        try:
            async_client = AsyncMock()
            async_client.__aenter__.return_value = async_client
            async_client.__aexit__.return_value = None

            with patch.object(main.httpx, "AsyncClient", return_value=async_client):
                await main.notify_backend_result(
                    try_on_id=123,
                    status="completed",
                    result_image_url="http://localhost:8004/uploads/results/result.jpg",
                    provider="local",
                )

            async_client.post.assert_awaited_once()
            _, kwargs = async_client.post.call_args
            self.assertEqual(
                kwargs["headers"],
                {"X-NailMind-Webhook-Secret": "backend-secret"},
            )
        finally:
            main.BACKEND_WEBHOOK_SECRET = original_secret

    async def test_backend_webhook_secret_defaults_to_legacy_ai_webhook_secret(self):
        with patch.dict("os.environ", {"AI_WEBHOOK_SECRET": "legacy-secret"}, clear=True):
            secret = main.resolve_backend_webhook_secret()

        self.assertEqual(secret, "legacy-secret")


if __name__ == "__main__":
    unittest.main()
