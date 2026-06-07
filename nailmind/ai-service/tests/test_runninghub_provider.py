import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app import main


class RunningHubProviderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_provider = main.TRYON_PROVIDER
        self.original_api_key = main.RUNNINGHUB_API_KEY
        self.original_timeout = main.RUNNINGHUB_TIMEOUT_SECONDS
        self.original_poll_interval = main.RUNNINGHUB_POLL_INTERVAL_SECONDS

    def tearDown(self):
        main.TRYON_PROVIDER = self.original_provider
        main.RUNNINGHUB_API_KEY = self.original_api_key
        main.RUNNINGHUB_TIMEOUT_SECONDS = self.original_timeout
        main.RUNNINGHUB_POLL_INTERVAL_SECONDS = self.original_poll_interval

    def test_auto_provider_without_key_fails_instead_of_falling_back(self):
        main.TRYON_PROVIDER = "auto"
        main.RUNNINGHUB_API_KEY = ""

        with self.assertRaises(HTTPException) as context:
            main.should_use_runninghub()

        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("RUNNINGHUB_API_KEY", context.exception.detail)

    def test_explicit_local_provider_is_rejected_because_local_tryon_fallback_is_disabled(self):
        main.TRYON_PROVIDER = "local"
        main.RUNNINGHUB_API_KEY = ""

        with self.assertRaises(HTTPException) as context:
            main.should_use_runninghub()

        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("Local try-on fallback is disabled", context.exception.detail)

    async def test_local_provider_notifies_failure_without_generating_fallback_image(self):
        main.TRYON_PROVIDER = "local"
        main.RUNNINGHUB_API_KEY = ""
        request = main.GenerateRequest(
            hand_photo_url="/uploads/hands/hand_01.jpg",
            design_image_url="/uploads/designs/design_01.jpg",
            try_on_id=9002,
        )

        with (
            patch.object(main, "generate_try_on_locally", AsyncMock(side_effect=AssertionError("local fallback should not be used"))),
            patch.object(main, "notify_backend_result", AsyncMock()) as notify_backend_result,
        ):
            await main.process_try_on_request(request)

        notify_backend_result.assert_awaited_once()
        _, kwargs = notify_backend_result.call_args
        self.assertEqual(kwargs["status"], "failed")
        self.assertEqual(kwargs["provider"], "runninghub")
        self.assertIn("Local try-on fallback is disabled", kwargs["error_message"])

    async def test_missing_runninghub_key_notifies_backend_without_local_generation(self):
        main.TRYON_PROVIDER = "auto"
        main.RUNNINGHUB_API_KEY = ""
        request = main.GenerateRequest(
            hand_photo_url="/uploads/hands/hand_01.jpg",
            design_image_url="/uploads/designs/design_01.jpg",
            try_on_id=9001,
        )

        with (
            patch.object(main, "generate_try_on_locally", AsyncMock(side_effect=AssertionError("local fallback should not be used"))),
            patch.object(main, "notify_backend_result", AsyncMock()) as notify_backend_result,
        ):
            await main.process_try_on_request(request)

        notify_backend_result.assert_awaited_once()
        _, kwargs = notify_backend_result.call_args
        self.assertEqual(kwargs["status"], "failed")
        self.assertEqual(kwargs["provider"], "runninghub")
        self.assertIn("RUNNINGHUB_API_KEY", kwargs["error_message"])

    def test_extract_result_url_accepts_runninghub_task_outputs_file_url(self):
        payload = {
            "code": 0,
            "msg": "success",
            "data": [
                {
                    "fileUrl": "https://example.com/output/result.png",
                    "fileType": "png",
                }
            ],
        }

        self.assertEqual(
            main.extract_result_url(payload),
            "https://example.com/output/result.png",
        )

    def test_extract_result_url_accepts_image_mime_output_type(self):
        payload = {
            "status": "SUCCESS",
            "results": [
                {
                    "url": "https://example.com/output/result.png",
                    "outputType": "image/png",
                }
            ],
        }

        self.assertEqual(
            main.extract_result_url(payload),
            "https://example.com/output/result.png",
        )

    async def test_http_exception_detail_is_reported_to_backend_failure(self):
        main.TRYON_PROVIDER = "runninghub"
        main.RUNNINGHUB_API_KEY = "configured"
        request = main.GenerateRequest(
            hand_photo_url="/uploads/hands/hand_01.jpg",
            design_image_url="/uploads/designs/design_01.jpg",
            try_on_id=9003,
        )

        with (
            patch.object(
                main,
                "generate_try_on_with_runninghub",
                AsyncMock(side_effect=HTTPException(status_code=502, detail="RunningHub task returned no image result")),
            ),
            patch.object(main, "notify_backend_result", AsyncMock()) as notify_backend_result,
        ):
            await main.process_try_on_request(request)

        _, kwargs = notify_backend_result.call_args
        self.assertEqual(kwargs["status"], "failed")
        self.assertEqual(kwargs["error_message"], "RunningHub task returned no image result")

    async def test_generation_queries_task_outputs_when_query_success_has_no_results(self):
        main.RUNNINGHUB_API_KEY = "configured"
        request = main.GenerateRequest(
            hand_photo_url="/uploads/hands/hand_01.jpg",
            design_image_url="/uploads/designs/design_01.jpg",
            try_on_id=9004,
        )

        with (
            patch.object(
                main,
                "download_source_image",
                AsyncMock(side_effect=[
                    ("hand.png", b"hand", "image/png"),
                    ("design.png", b"design", "image/png"),
                ]),
            ),
            patch.object(
                main,
                "upload_runninghub_media",
                AsyncMock(side_effect=["api/hand.png", "api/design.png"]),
            ),
            patch.object(main, "submit_runninghub_task", AsyncMock(return_value="task-9004")),
            patch.object(
                main,
                "query_runninghub_until_done",
                AsyncMock(return_value={"taskId": "task-9004", "status": "SUCCESS", "results": None}),
            ),
            patch.object(
                main,
                "query_runninghub_task_outputs",
                AsyncMock(return_value={
                    "code": 0,
                    "msg": "success",
                    "data": [{"fileUrl": "https://example.com/output/result.png", "fileType": "png"}],
                }),
                create=True,
            ) as query_runninghub_task_outputs,
            patch.object(main, "save_remote_result", AsyncMock(return_value="/uploads/results/result.png")) as save_remote_result,
        ):
            result_url = await main.generate_try_on_with_runninghub(request)

        query_runninghub_task_outputs.assert_awaited_once()
        save_remote_result.assert_awaited_once()
        self.assertEqual(save_remote_result.call_args.args[1], "https://example.com/output/result.png")
        self.assertEqual(result_url, "/uploads/results/result.png")

    async def test_query_runninghub_until_done_keeps_polling_after_transient_request_error(self):
        main.RUNNINGHUB_API_KEY = "configured"
        main.RUNNINGHUB_TIMEOUT_SECONDS = 20
        main.RUNNINGHUB_POLL_INTERVAL_SECONDS = 0

        success_response = unittest.mock.Mock()
        success_response.raise_for_status.return_value = None
        success_response.json.return_value = {
            "taskId": "task-9005",
            "status": "SUCCESS",
            "results": [{"url": "https://example.com/output/result.png", "outputType": "png"}],
        }
        client = unittest.mock.Mock()
        client.post = AsyncMock(side_effect=[main.httpx.ReadTimeout(""), success_response])

        with patch.object(main.asyncio, "sleep", AsyncMock()):
            payload = await main.query_runninghub_until_done(client, "task-9005")

        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(client.post.await_count, 2)


if __name__ == "__main__":
    unittest.main()
