from datetime import datetime, timedelta, timezone
import unittest


class TryOnProgressTest(unittest.TestCase):
    def _utc_now_naive(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def test_processing_progress_is_derived_from_record_age(self):
        from app import models
        from app.routers.tryon import build_try_on_progress

        try_on = models.TryOnRecord(
            id=42,
            status="processing",
            created_at=self._utc_now_naive() - timedelta(seconds=45),
        )

        progress = build_try_on_progress(try_on)

        self.assertEqual(progress["try_on_id"], 42)
        self.assertEqual(progress["status"], "processing")
        self.assertGreaterEqual(progress["progress"], 50)
        self.assertLess(progress["progress"], 100)
        self.assertTrue(progress["message"])

    def test_completed_progress_exposes_result_url(self):
        from app import models
        from app.routers.tryon import build_try_on_progress

        try_on = models.TryOnRecord(
            id=7,
            status="completed",
            result_image_url="/uploads/results/result_7.png",
            created_at=self._utc_now_naive() - timedelta(seconds=15),
            completed_at=self._utc_now_naive(),
        )

        progress = build_try_on_progress(try_on)

        self.assertEqual(progress["progress"], 100)
        self.assertEqual(progress["phase"], "completed")
        self.assertEqual(progress["result_image_url"], "/uploads/results/result_7.png")

    def test_fallback_completed_progress_is_treated_as_failed_not_displayable_result(self):
        from app import models
        from app.routers.tryon import build_try_on_progress

        try_on = models.TryOnRecord(
            id=8,
            status="fallback_completed",
            result_image_url="/uploads/results/fallback_8.png",
            created_at=self._utc_now_naive() - timedelta(seconds=15),
            completed_at=self._utc_now_naive(),
        )

        progress = build_try_on_progress(try_on)

        self.assertEqual(progress["status"], "failed")
        self.assertEqual(progress["phase"], "failed")
        self.assertIsNone(progress["result_image_url"])
        self.assertIn("AI 试戴生成失败", progress["message"])

    def test_long_running_progress_keeps_elapsed_time_and_moves_past_95(self):
        from app import models
        from app.routers.tryon import build_try_on_progress

        try_on = models.TryOnRecord(
            id=99,
            status="processing",
            created_at=self._utc_now_naive() - timedelta(seconds=180),
        )

        progress = build_try_on_progress(try_on)

        self.assertEqual(progress["try_on_id"], 99)
        self.assertEqual(progress["phase"], "waiting")
        self.assertGreaterEqual(progress["elapsed_seconds"], 175)
        self.assertGreater(progress["progress"], 95)
        self.assertLess(progress["progress"], 100)
        self.assertIsNotNone(progress["started_at"])

    def test_recent_database_utc_timestamp_does_not_look_eight_hours_old(self):
        from app import models
        from app.routers.tryon import build_try_on_progress

        try_on = models.TryOnRecord(
            id=100,
            status="processing",
            created_at=self._utc_now_naive(),
        )

        progress = build_try_on_progress(try_on)

        self.assertLess(progress["elapsed_seconds"], 5)
        self.assertLess(progress["progress"], 20)


if __name__ == "__main__":
    unittest.main()
