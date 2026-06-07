import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


class TryOnWebhookContractTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def _seed_processing_tryon(self) -> int:
        from app import models

        db = self.SessionLocal()
        try:
            user = models.User(phone="13940001001", nickname="Webhook User")
            db.add(user)
            db.flush()

            hand_photo = models.HandPhoto(user_id=user.id, image_url="/uploads/hands/webhook-hand.jpg")
            design = models.NailDesign(
                name="Webhook Design",
                image_url="/uploads/designs/webhook-design.jpg",
                status="active",
            )
            db.add_all([hand_photo, design])
            db.flush()

            try_on = models.TryOnRecord(
                user_id=user.id,
                hand_photo_id=hand_photo.id,
                nail_design_id=design.id,
                status="processing",
            )
            db.add(try_on)
            db.commit()
            return try_on.id
        finally:
            db.close()

    def _design_try_on_count(self, try_on_id: int) -> int:
        from app import models

        db = self.SessionLocal()
        try:
            try_on = db.query(models.TryOnRecord).filter(models.TryOnRecord.id == try_on_id).first()
            design = db.query(models.NailDesign).filter(models.NailDesign.id == try_on.nail_design_id).first()
            return design.try_on_count
        finally:
            db.close()

    def _tryon_status(self, try_on_id: int) -> tuple[str, str | None]:
        from app import models

        db = self.SessionLocal()
        try:
            try_on = db.query(models.TryOnRecord).filter(models.TryOnRecord.id == try_on_id).first()
            return try_on.status, try_on.result_image_url
        finally:
            db.close()

    def _tryon_completed_at(self, try_on_id: int):
        from app import models

        db = self.SessionLocal()
        try:
            try_on = db.query(models.TryOnRecord).filter(models.TryOnRecord.id == try_on_id).first()
            return try_on.completed_at
        finally:
            db.close()

    @patch("app.routers.tryon.settings")
    def test_production_webhook_requires_configured_secret(self, mocked_settings):
        mocked_settings.DEBUG = False
        mocked_settings.AI_WEBHOOK_SECRET = ""
        try_on_id = self._seed_processing_tryon()

        response = self.client.post(
            "/api/tryon/webhook/result",
            json={
                "try_on_id": try_on_id,
                "status": "completed",
                "result_image_url": "/uploads/results/forged.png",
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "AI webhook secret is not configured")
        self.assertEqual(self._tryon_status(try_on_id), ("processing", None))

    def test_webhook_rejects_unknown_result_status(self):
        try_on_id = self._seed_processing_tryon()

        response = self.client.post(
            "/api/tryon/webhook/result",
            json={
                "try_on_id": try_on_id,
                "status": "done",
                "result_image_url": "/uploads/results/invalid-status.png",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid try-on result status")
        self.assertEqual(self._tryon_status(try_on_id), ("processing", None))

    def test_webhook_rejects_completed_result_without_image_url(self):
        try_on_id = self._seed_processing_tryon()

        response = self.client.post(
            "/api/tryon/webhook/result",
            json={
                "try_on_id": try_on_id,
                "status": "completed",
                "result_image_url": None,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Completed try-on result requires result_image_url")
        self.assertEqual(self._tryon_status(try_on_id), ("processing", None))

    def test_webhook_increments_design_tryon_count_only_for_completed_result_once(self):
        try_on_id = self._seed_processing_tryon()

        first_response = self.client.post(
            "/api/tryon/webhook/result",
            json={
                "try_on_id": try_on_id,
                "status": "completed",
                "result_image_url": "/uploads/results/completed-once.png",
            },
        )
        duplicate_response = self.client.post(
            "/api/tryon/webhook/result",
            json={
                "try_on_id": try_on_id,
                "status": "completed",
                "result_image_url": "/uploads/results/completed-once-again.png",
            },
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertEqual(self._design_try_on_count(try_on_id), 1)

    def test_duplicate_completed_webhook_does_not_replace_stable_result_image(self):
        try_on_id = self._seed_processing_tryon()

        first_response = self.client.post(
            "/api/tryon/webhook/result",
            json={
                "try_on_id": try_on_id,
                "status": "completed",
                "result_image_url": "/uploads/results/first-evidence.png",
            },
        )
        duplicate_response = self.client.post(
            "/api/tryon/webhook/result",
            json={
                "try_on_id": try_on_id,
                "status": "completed",
                "result_image_url": "/uploads/results/late-replacement.png",
            },
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertEqual(self._tryon_status(try_on_id), ("completed", "/uploads/results/first-evidence.png"))

    def test_webhook_failed_result_does_not_increment_design_tryon_count(self):
        try_on_id = self._seed_processing_tryon()

        response = self.client.post(
            "/api/tryon/webhook/result",
            json={
                "try_on_id": try_on_id,
                "status": "failed",
                "error_message": "AI service unavailable",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._design_try_on_count(try_on_id), 0)

    def test_webhook_failed_result_records_terminal_timestamp(self):
        try_on_id = self._seed_processing_tryon()

        response = self.client.post(
            "/api/tryon/webhook/result",
            json={
                "try_on_id": try_on_id,
                "status": "failed",
                "error_message": "provider returned failed",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self._tryon_completed_at(try_on_id))

    def test_late_failed_webhook_does_not_overwrite_completed_result(self):
        try_on_id = self._seed_processing_tryon()

        completed_response = self.client.post(
            "/api/tryon/webhook/result",
            json={
                "try_on_id": try_on_id,
                "status": "completed",
                "result_image_url": "/uploads/results/stable-completed.png",
            },
        )
        failed_response = self.client.post(
            "/api/tryon/webhook/result",
            json={
                "try_on_id": try_on_id,
                "status": "failed",
                "error_message": "late provider failure",
            },
        )

        self.assertEqual(completed_response.status_code, 200)
        self.assertEqual(failed_response.status_code, 200)
        self.assertEqual(self._tryon_status(try_on_id), ("completed", "/uploads/results/stable-completed.png"))
        self.assertEqual(self._design_try_on_count(try_on_id), 1)


if __name__ == "__main__":
    unittest.main()
