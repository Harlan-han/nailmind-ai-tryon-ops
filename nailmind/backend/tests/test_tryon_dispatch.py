import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base


class TryOnDispatchContractTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from app import models  # noqa: F401 - registers tables on Base metadata

        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _seed_processing_tryon(self) -> int:
        from app import models

        db = self.SessionLocal()
        try:
            user = models.User(phone="13932000001", nickname="Dispatch User")
            db.add(user)
            db.flush()
            hand_photo = models.HandPhoto(user_id=user.id, image_url="/uploads/hands/dispatch-hand.jpg")
            design = models.NailDesign(
                name="Dispatch Design",
                image_url="/uploads/designs/dispatch-design.jpg",
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

    async def test_ai_dispatch_failure_marks_tryon_failed(self):
        from app import models
        from app.routers import tryon

        try_on_id = self._seed_processing_tryon()

        async_client = AsyncMock()
        async_client.post.side_effect = RuntimeError("AI service unavailable")
        async_client.__aenter__.return_value = async_client
        async_client.__aexit__.return_value = None

        with patch.object(tryon, "SessionLocal", self.SessionLocal, create=True), patch(
            "app.routers.tryon.httpx.AsyncClient",
            return_value=async_client,
        ):
            result = await tryon.dispatch_ai_generation(
                "/uploads/hands/dispatch-hand.jpg",
                "/uploads/designs/dispatch-design.jpg",
                try_on_id,
            )

        db = self.SessionLocal()
        try:
            record = db.query(models.TryOnRecord).filter(models.TryOnRecord.id == try_on_id).first()
        finally:
            db.close()

        self.assertIsNone(result)
        self.assertEqual(record.status, "failed")
        self.assertIn("AI service unavailable", record.error_message)
        self.assertIsNotNone(record.completed_at)


if __name__ == "__main__":
    unittest.main()
