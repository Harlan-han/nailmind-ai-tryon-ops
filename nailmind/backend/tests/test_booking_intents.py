import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import clear_login_codes
from app import models
from app.database import Base, get_db
from app.main import app


class BookingIntentFlowTest(unittest.TestCase):
    def _create_memory_db(self):
        from app.database import Base

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine)()

    def _seed_tryon(self, db):
        from app import models

        user = models.User(phone="18812345678", nickname="Harlan")
        db.add(user)
        db.flush()

        hand_photo = models.HandPhoto(user_id=user.id, image_url="/uploads/hands/test.jpg")
        db.add(hand_photo)
        db.flush()

        design = models.NailDesign(
            name="真实预约测试款",
            image_url="/uploads/designs/test.jpg",
            style_tags=["法式"],
            color_tags=["裸色"],
            scene_tags=["通勤"],
            status="active",
            booking_count=0,
        )
        db.add(design)
        db.flush()

        try_on = models.TryOnRecord(
            user_id=user.id,
            hand_photo_id=hand_photo.id,
            nail_design_id=design.id,
            result_image_url="/uploads/results/test.png",
            status="completed",
        )
        db.add(try_on)
        db.commit()
        return user, design, try_on

    def test_create_booking_intent_updates_tryon_and_design_counters(self):
        from app import schemas
        from app.routers import operations

        db = self._create_memory_db()
        user, design, try_on = self._seed_tryon(db)

        response = operations.create_booking_intent(
            schemas.BookingIntentCreate(
                try_on_record_id=try_on.id,
                nail_design_id=design.id,
                phone="18812345678",
                preferred_date=datetime.now() + timedelta(days=1),
                notes="下午到店",
            ),
            current_user=user,
            db=db,
        )

        db.refresh(try_on)
        db.refresh(design)
        self.assertTrue(try_on.has_booking_intent)
        self.assertEqual(design.booking_count, 1)
        self.assertEqual(response.status, "pending")

    def test_create_booking_intent_is_idempotent_per_tryon(self):
        from app import schemas
        from app.routers import operations

        db = self._create_memory_db()
        user, design, try_on = self._seed_tryon(db)
        payload = schemas.BookingIntentCreate(
            try_on_record_id=try_on.id,
            nail_design_id=design.id,
            phone="18812345678",
        )

        first = operations.create_booking_intent(payload, current_user=user, db=db)
        second = operations.create_booking_intent(payload, current_user=user, db=db)

        db.refresh(design)
        self.assertEqual(first.id, second.id)
        self.assertEqual(design.booking_count, 1)

    def test_list_booking_intents_returns_followup_context(self):
        from app import schemas
        from app.routers import operations

        db = self._create_memory_db()
        user, design, try_on = self._seed_tryon(db)
        operations.create_booking_intent(
            schemas.BookingIntentCreate(
                try_on_record_id=try_on.id,
                nail_design_id=design.id,
                phone="18812345678",
                notes="需要确认时间",
            ),
            current_user=user,
            db=db,
        )

        items = operations.list_booking_intents(db=db)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["user_name"], "Harlan")
        self.assertEqual(items[0]["design_name"], "真实预约测试款")
        self.assertEqual(items[0]["try_on_result_image_url"], "/uploads/results/test.png")

    def test_update_booking_intent_status_persists(self):
        from app import schemas
        from app.routers import operations

        db = self._create_memory_db()
        user, _, try_on = self._seed_tryon(db)
        booking = operations.create_booking_intent(
            schemas.BookingIntentCreate(
                try_on_record_id=try_on.id,
                nail_design_id=try_on.nail_design_id,
                phone="18812345678",
            ),
            current_user=user,
            db=db,
        )

        operations.update_booking_intent_status(booking.id, status="contacted", db=db)
        updated = operations.update_booking_intent_status(booking.id, status="confirmed", db=db)

        self.assertEqual(updated["status"], "confirmed")
        self.assertEqual(operations.list_booking_intents(status="confirmed", db=db)[0]["id"], booking.id)

    def test_update_booking_intent_status_rejects_skipped_followup_steps(self):
        from fastapi import HTTPException
        from app import schemas
        from app.routers import operations

        db = self._create_memory_db()
        user, _, try_on = self._seed_tryon(db)
        booking = operations.create_booking_intent(
            schemas.BookingIntentCreate(
                try_on_record_id=try_on.id,
                nail_design_id=try_on.nail_design_id,
                phone="18812345678",
            ),
            current_user=user,
            db=db,
        )

        with self.assertRaises(HTTPException) as context:
            operations.update_booking_intent_status(booking.id, status="completed", db=db)

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("Invalid booking status transition", context.exception.detail)

    def test_update_booking_intent_status_allows_linear_progression_and_cancellation(self):
        from fastapi import HTTPException
        from app import schemas
        from app.routers import operations

        db = self._create_memory_db()
        user, _, try_on = self._seed_tryon(db)
        booking = operations.create_booking_intent(
            schemas.BookingIntentCreate(
                try_on_record_id=try_on.id,
                nail_design_id=try_on.nail_design_id,
                phone="18812345678",
            ),
            current_user=user,
            db=db,
        )

        self.assertEqual(
            operations.update_booking_intent_status(booking.id, status="contacted", db=db)["status"],
            "contacted",
        )
        self.assertEqual(
            operations.update_booking_intent_status(booking.id, status="confirmed", db=db)["status"],
            "confirmed",
        )
        self.assertEqual(
            operations.update_booking_intent_status(booking.id, status="completed", db=db)["status"],
            "completed",
        )

        with self.assertRaises(HTTPException):
            operations.update_booking_intent_status(booking.id, status="cancelled", db=db)


class BookingIntentHttpContractTest(unittest.TestCase):
    def setUp(self):
        clear_login_codes()
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

    def _login(self, phone: str, user_type: str = "consumer") -> tuple[str, dict]:
        code_response = self.client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": f"User {phone[-4:]}", "user_type": user_type},
        )
        self.assertEqual(code_response.status_code, 200)

        login_response = self.client.post(
            "/api/auth/login",
            json={
                "phone": phone,
                "code": code_response.json()["debug_code"],
                "nickname": f"User {phone[-4:]}",
                "user_type": user_type,
            },
        )
        self.assertEqual(login_response.status_code, 200)
        body = login_response.json()
        return body["access_token"], body["user"]

    def _seed_tryon_with_status(
        self,
        user_id: int,
        status: str = "completed",
        result_image_url: str | None = "/uploads/results/contract-result.png",
    ) -> tuple[int, int]:
        from app import models

        db = self.SessionLocal()
        try:
            hand_photo = models.HandPhoto(user_id=user_id, image_url="/uploads/hands/contract-hand.jpg")
            db.add(hand_photo)
            db.flush()

            design = models.NailDesign(
                name="Cherry Chrome",
                description="Red chrome short nail design",
                image_url="/uploads/designs/cherry-chrome.jpg",
                style_tags=["chrome", "minimal"],
                color_tags=["red"],
                scene_tags=["daily"],
                status="active",
                try_on_count=1,
                booking_count=0,
            )
            db.add(design)
            db.flush()

            try_on = models.TryOnRecord(
                user_id=user_id,
                hand_photo_id=hand_photo.id,
                nail_design_id=design.id,
                result_image_url=result_image_url,
                status=status,
                completed_at=datetime.now() if status in {"completed", "fallback_completed"} else None,
            )
            db.add(try_on)
            db.commit()
            return design.id, try_on.id
        finally:
            db.close()

    def _seed_completed_tryon(self, user_id: int) -> tuple[int, int]:
        return self._seed_tryon_with_status(user_id=user_id)

    def _seed_merchant_overview_data(self, user_id: int) -> None:
        from app import models

        db = self.SessionLocal()
        try:
            now = datetime.now()
            hand_photo = models.HandPhoto(user_id=user_id, image_url="/uploads/hands/overview-hand.jpg")
            db.add(hand_photo)
            db.flush()

            chrome = models.NailDesign(
                name="Cherry Chrome",
                image_url="/uploads/designs/cherry-chrome.jpg",
                style_tags=["chrome"],
                color_tags=["red"],
                scene_tags=["party"],
                status="active",
                view_count=120,
                try_on_count=3,
                favorite_count=2,
                booking_count=1,
            )
            french = models.NailDesign(
                name="Nude French",
                image_url="/uploads/designs/nude-french.jpg",
                style_tags=["french"],
                color_tags=["nude"],
                scene_tags=["daily"],
                status="active",
                view_count=80,
                try_on_count=1,
                favorite_count=0,
                booking_count=0,
            )
            archived = models.NailDesign(
                name="Archived Cat Eye",
                image_url="/uploads/designs/archived-cat-eye.jpg",
                status="inactive",
                view_count=0,
                try_on_count=0,
                favorite_count=0,
                booking_count=0,
            )
            db.add_all([chrome, french, archived])
            db.flush()

            try_ons = [
                models.TryOnRecord(
                    user_id=user_id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=chrome.id,
                    result_image_url=f"/uploads/results/chrome-{index}.png",
                    status="completed",
                    created_at=now - timedelta(minutes=10 - index),
                    completed_at=now - timedelta(minutes=10 - index),
                    is_favorite=index < 2,
                    has_booking_intent=index == 0,
                )
                for index in range(3)
            ]
            try_ons.append(
                models.TryOnRecord(
                    user_id=user_id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=french.id,
                    result_image_url="/uploads/results/french.png",
                    status="completed",
                    created_at=now - timedelta(minutes=20),
                    completed_at=now - timedelta(minutes=20),
                )
            )
            db.add_all(try_ons)
            db.flush()

            db.add_all(
                [
                    models.Favorite(
                        user_id=user_id,
                        nail_design_id=chrome.id,
                        try_on_record_id=try_ons[0].id,
                        created_at=now - timedelta(minutes=2),
                    ),
                    models.Favorite(
                        user_id=user_id,
                        nail_design_id=chrome.id,
                        try_on_record_id=try_ons[1].id,
                        created_at=now - timedelta(minutes=3),
                    ),
                ]
            )
            db.add(
                models.BookingIntent(
                    user_id=user_id,
                    try_on_record_id=try_ons[0].id,
                    nail_design_id=chrome.id,
                    phone="13920001005",
                    notes="wants weekend appointment",
                    status="pending",
                    created_at=now - timedelta(minutes=1),
                )
            )
            db.commit()
        finally:
            db.close()

    def _seed_failed_tryon_overview_data(self, user_id: int) -> None:
        from app import models

        db = self.SessionLocal()
        try:
            hand_photo = models.HandPhoto(user_id=user_id, image_url="/uploads/hands/failed-overview-hand.jpg")
            db.add(hand_photo)
            db.flush()

            design = models.NailDesign(
                name="Broken Chrome",
                image_url="/uploads/designs/broken-chrome.jpg",
                style_tags=["chrome"],
                color_tags=["silver"],
                scene_tags=["party"],
                status="active",
                try_on_count=1,
            )
            db.add(design)
            db.flush()

            db.add(
                models.TryOnRecord(
                    user_id=user_id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=design.id,
                    status="failed",
                    error_message="AI service unavailable",
                    created_at=datetime.now() - timedelta(minutes=2),
                    completed_at=datetime.now() - timedelta(minutes=2),
                )
            )
            db.commit()
        finally:
            db.close()

    def _seed_operations_signal_quality_data(self, user_id: int) -> None:
        from app import models

        db = self.SessionLocal()
        try:
            now = datetime.now()
            hand_photo = models.HandPhoto(user_id=user_id, image_url="/uploads/hands/signal-quality-hand.jpg")
            db.add(hand_photo)
            db.flush()

            valid_design = models.NailDesign(
                name="Valid Demand",
                image_url="/uploads/designs/valid-demand.jpg",
                style_tags=["valid-style"],
                color_tags=["valid-color"],
                scene_tags=["daily"],
                status="active",
                view_count=100,
            )
            fallback_design = models.NailDesign(
                name="Fallback Demand",
                image_url="/uploads/designs/fallback-demand.jpg",
                style_tags=["fallback-style"],
                color_tags=["fallback-color"],
                scene_tags=["daily"],
                status="active",
                view_count=20,
            )
            failed_design = models.NailDesign(
                name="Failed Noise",
                image_url="/uploads/designs/failed-noise.jpg",
                style_tags=["failed-style"],
                color_tags=["failed-color"],
                scene_tags=["daily"],
                status="active",
                view_count=0,
            )
            processing_design = models.NailDesign(
                name="Processing Noise",
                image_url="/uploads/designs/processing-noise.jpg",
                style_tags=["processing-style"],
                color_tags=["processing-color"],
                scene_tags=["daily"],
                status="active",
                view_count=0,
            )
            db.add_all([valid_design, fallback_design, failed_design, processing_design])
            db.flush()

            db.add_all(
                [
                    models.TryOnRecord(
                        user_id=user_id,
                        hand_photo_id=hand_photo.id,
                        nail_design_id=valid_design.id,
                        result_image_url="/uploads/results/valid-demand.png",
                        status="completed",
                        created_at=now - timedelta(minutes=10),
                        completed_at=now - timedelta(minutes=9),
                    ),
                    models.TryOnRecord(
                        user_id=user_id,
                        hand_photo_id=hand_photo.id,
                        nail_design_id=fallback_design.id,
                        result_image_url="/uploads/results/fallback-demand.png",
                        status="fallback_completed",
                        created_at=now - timedelta(minutes=8),
                        completed_at=now - timedelta(minutes=7),
                    ),
                    models.TryOnRecord(
                        user_id=user_id,
                        hand_photo_id=hand_photo.id,
                        nail_design_id=failed_design.id,
                        status="failed",
                        error_message="AI service unavailable",
                        created_at=now - timedelta(minutes=6),
                        completed_at=now - timedelta(minutes=5),
                    ),
                    models.TryOnRecord(
                        user_id=user_id,
                        hand_photo_id=hand_photo.id,
                        nail_design_id=processing_design.id,
                        status="processing",
                        created_at=now - timedelta(minutes=4),
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

    def test_consumer_booking_intent_is_visible_in_operator_followup_queue(self):
        consumer_token, consumer = self._login("13920001001", "consumer")
        admin_token, _ = self._login("13920001002", "admin")
        design_id, try_on_id = self._seed_completed_tryon(consumer["id"])

        create_response = self.client.post(
            "/api/operations/booking-intents",
            headers={"Authorization": f"Bearer {consumer_token}"},
            json={
                "try_on_record_id": try_on_id,
                "nail_design_id": design_id,
                "phone": "13920001001",
                "notes": "prefers weekend appointment",
            },
        )

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["status"], "pending")

        records_response = self.client.get(
            "/api/tryon/me/records",
            headers={"Authorization": f"Bearer {consumer_token}"},
        )
        self.assertEqual(records_response.status_code, 200)
        records = records_response.json()
        self.assertEqual(records[0]["id"], try_on_id)
        self.assertTrue(records[0]["has_booking_intent"])
        self.assertEqual(records[0]["nail_design"]["booking_count"], 1)

        consumer_queue_response = self.client.get(
            "/api/operations/booking-intents",
            headers={"Authorization": f"Bearer {consumer_token}"},
        )
        self.assertEqual(consumer_queue_response.status_code, 403)

        operator_queue_response = self.client.get(
            "/api/operations/booking-intents?status=pending",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(operator_queue_response.status_code, 200)
        queue_items = operator_queue_response.json()
        self.assertEqual(len(queue_items), 1)
        self.assertEqual(queue_items[0]["try_on_record_id"], try_on_id)
        self.assertEqual(queue_items[0]["design_name"], "Cherry Chrome")
        self.assertEqual(queue_items[0]["try_on_result_image_url"], "/uploads/results/contract-result.png")

        from app.operations_agent.tools import OperationsToolRegistry

        db = self.SessionLocal()
        try:
            tool_result = OperationsToolRegistry().execute(
                "get_booking_followups",
                {"status": "pending", "limit": 5},
                db,
            )
        finally:
            db.close()

        tool_items = tool_result["data"]["items"]
        self.assertEqual(len(tool_items), 1)
        self.assertEqual(tool_items[0]["try_on_record_id"], try_on_id)
        self.assertEqual(tool_items[0]["phone"], "13920001001")

    def test_booking_intent_normalizes_phone_for_operator_followup(self):
        consumer_token, consumer = self._login("13920001041", "consumer")
        admin_token, _ = self._login("13920001042", "admin")
        design_id, try_on_id = self._seed_completed_tryon(consumer["id"])

        create_response = self.client.post(
            "/api/operations/booking-intents",
            headers={"Authorization": f"Bearer {consumer_token}"},
            json={
                "try_on_record_id": try_on_id,
                "nail_design_id": design_id,
                "phone": " 139-2000-1041 ",
                "notes": "initial",
            },
        )
        update_response = self.client.post(
            "/api/operations/booking-intents",
            headers={"Authorization": f"Bearer {consumer_token}"},
            json={
                "try_on_record_id": try_on_id,
                "nail_design_id": design_id,
                "phone": " 139 2000 1041 ",
                "notes": "updated",
            },
        )

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["phone"], "13920001041")
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["phone"], "13920001041")

        operator_queue_response = self.client.get(
            "/api/operations/booking-intents?status=pending",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(operator_queue_response.status_code, 200)
        queue_items = operator_queue_response.json()
        self.assertEqual(queue_items[0]["phone"], "13920001041")
        self.assertEqual(queue_items[0]["notes"], "updated")

    def test_operator_cannot_skip_booking_followup_status_steps(self):
        consumer_token, consumer = self._login("13920001039", "consumer")
        admin_token, _ = self._login("13920001040", "admin")
        design_id, try_on_id = self._seed_completed_tryon(consumer["id"])

        create_response = self.client.post(
            "/api/operations/booking-intents",
            headers={"Authorization": f"Bearer {consumer_token}"},
            json={
                "try_on_record_id": try_on_id,
                "nail_design_id": design_id,
                "phone": "13920001039",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        booking_id = create_response.json()["id"]

        skip_response = self.client.patch(
            f"/api/operations/booking-intents/{booking_id}/status?status=completed",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(skip_response.status_code, 400)
        self.assertIn("Invalid booking status transition", skip_response.json()["detail"])

    def test_operator_booking_list_rejects_unbounded_limit(self):
        admin_token, _ = self._login("13920001043", "admin")

        zero_response = self.client.get(
            "/api/operations/booking-intents?limit=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        negative_response = self.client.get(
            "/api/operations/booking-intents?limit=-1",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(zero_response.status_code, 422)
        self.assertEqual(negative_response.status_code, 422)

    def test_consumer_cannot_book_another_users_tryon(self):
        owner_token, owner = self._login("13920001003", "consumer")
        other_token, _ = self._login("13920001004", "consumer")
        design_id, try_on_id = self._seed_completed_tryon(owner["id"])

        response = self.client.post(
            "/api/operations/booking-intents",
            headers={"Authorization": f"Bearer {other_token}"},
            json={
                "try_on_record_id": try_on_id,
                "nail_design_id": design_id,
                "phone": "13920001004",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(owner_token)

    def test_consumer_cannot_book_unfinished_tryon(self):
        consumer_token, consumer = self._login("13920001015", "consumer")
        design_id, try_on_id = self._seed_tryon_with_status(
            consumer["id"],
            status="processing",
            result_image_url=None,
        )

        response = self.client.post(
            "/api/operations/booking-intents",
            headers={"Authorization": f"Bearer {consumer_token}"},
            json={
                "try_on_record_id": try_on_id,
                "nail_design_id": design_id,
                "phone": "13920001015",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Try-on result is not ready for booking")

    def test_consumer_cannot_book_failed_tryon_even_with_result_url(self):
        consumer_token, consumer = self._login("13920001016", "consumer")
        design_id, try_on_id = self._seed_tryon_with_status(
            consumer["id"],
            status="failed",
            result_image_url="/uploads/results/stale.png",
        )

        response = self.client.post(
            "/api/operations/booking-intents",
            headers={"Authorization": f"Bearer {consumer_token}"},
            json={
                "try_on_record_id": try_on_id,
                "nail_design_id": design_id,
                "phone": "13920001016",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Try-on result is not ready for booking")

    def test_consumer_cannot_read_merchant_overview(self):
        consumer_token, _ = self._login("13920001005", "consumer")

        response = self.client.get(
            "/api/operations/merchant-overview",
            headers={"Authorization": f"Bearer {consumer_token}"},
        )

        self.assertEqual(response.status_code, 403)

    def test_operator_merchant_overview_uses_live_business_data(self):
        consumer_token, consumer = self._login("13920001006", "consumer")
        admin_token, _ = self._login("13920001007", "admin")
        self._seed_merchant_overview_data(consumer["id"])

        response = self.client.get(
            "/api/operations/merchant-overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_designs"], 3)
        self.assertEqual(body["active_designs"], 2)
        self.assertEqual(body["total_views"], 200)
        self.assertEqual(body["total_try_ons"], 4)
        self.assertEqual(body["total_favorites"], 2)
        self.assertEqual(body["recent_bookings"], 1)
        self.assertEqual(body["conversion_rate"], 50.0)
        self.assertEqual(body["hot_designs"][0]["name"], "Cherry Chrome")
        self.assertEqual(body["hot_designs"][0]["try_on_count"], 3)
        self.assertEqual(body["recent_activity"][0]["action"], "提交预约")
        self.assertIn("Cherry Chrome", body["recent_activity"][0]["detail"])
        self.assertTrue(consumer_token)

    def test_merchant_overview_activity_items_have_stable_unique_event_keys(self):
        _, consumer = self._login("13920001031", "consumer")
        admin_token, _ = self._login("13920001032", "admin")

        db = self.SessionLocal()
        try:
            design = models.NailDesign(
                name="Duplicate Activity Chrome",
                image_url="/uploads/designs/duplicate-activity.jpg",
                style_tags=["chrome"],
                color_tags=["silver"],
                scene_tags=["party"],
                status="active",
            )
            db.add(design)
            db.flush()

            same_second = datetime.now(timezone.utc).replace(microsecond=0)
            db.add_all([
                models.Favorite(
                    user_id=consumer["id"],
                    nail_design_id=design.id,
                    created_at=same_second,
                ),
                models.Favorite(
                    user_id=consumer["id"],
                    nail_design_id=design.id,
                    created_at=same_second,
                ),
            ])
            db.commit()
        finally:
            db.close()

        response = self.client.get(
            "/api/operations/merchant-overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        favorite_events = [
            item for item in response.json()["recent_activity"]
            if item["detail"] == "Duplicate Activity Chrome"
        ]
        self.assertGreaterEqual(len(favorite_events), 2)
        event_keys = [item["event_key"] for item in favorite_events]
        self.assertEqual(len(event_keys), len(set(event_keys)))
        self.assertTrue(all(key.startswith("favorite_") for key in event_keys))

    def test_merchant_overview_tryon_activity_keys_use_tryon_identity(self):
        _, consumer = self._login("13920001033", "consumer")
        admin_token, _ = self._login("13920001034", "admin")

        db = self.SessionLocal()
        try:
            hand_photo = models.HandPhoto(
                user_id=consumer["id"],
                image_url="/uploads/hands/duplicate-tryon-hand.jpg",
            )
            design = models.NailDesign(
                name="Duplicate TryOn Chrome",
                image_url="/uploads/designs/duplicate-tryon.jpg",
                style_tags=["chrome"],
                color_tags=["silver"],
                scene_tags=["party"],
                status="active",
            )
            db.add_all([hand_photo, design])
            db.flush()

            same_second = datetime.now(timezone.utc).replace(microsecond=0)
            db.add_all([
                models.TryOnRecord(
                    user_id=consumer["id"],
                    hand_photo_id=hand_photo.id,
                    nail_design_id=design.id,
                    result_image_url="/uploads/results/duplicate-tryon-a.png",
                    status="completed",
                    created_at=same_second,
                    completed_at=same_second,
                ),
                models.TryOnRecord(
                    user_id=consumer["id"],
                    hand_photo_id=hand_photo.id,
                    nail_design_id=design.id,
                    result_image_url="/uploads/results/duplicate-tryon-b.png",
                    status="completed",
                    created_at=same_second,
                    completed_at=same_second,
                ),
            ])
            db.commit()
        finally:
            db.close()

        response = self.client.get(
            "/api/operations/merchant-overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        tryon_events = [
            item for item in response.json()["recent_activity"]
            if item["detail"] == "Duplicate TryOn Chrome"
        ]
        self.assertGreaterEqual(len(tryon_events), 2)
        event_keys = [item["event_key"] for item in tryon_events]
        self.assertEqual(len(event_keys), len(set(event_keys)))
        self.assertTrue(all(key.startswith("tryon_") for key in event_keys))

    def test_operator_merchant_overview_exposes_failed_tryon_diagnostics(self):
        _, consumer = self._login("13920001017", "consumer")
        admin_token, _ = self._login("13920001018", "admin")
        self._seed_failed_tryon_overview_data(consumer["id"])

        response = self.client.get(
            "/api/operations/merchant-overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["failed_try_ons"], 1)
        self.assertEqual(body["recent_activity"][0]["action"], "试戴失败")
        self.assertIn("Broken Chrome", body["recent_activity"][0]["detail"])
        self.assertIn("AI service unavailable", body["recent_activity"][0]["detail"])

    def test_merchant_overview_conversion_uses_completed_tryons_only(self):
        _, consumer = self._login("13920001035", "consumer")
        admin_token, _ = self._login("13920001036", "admin")
        self._seed_operations_signal_quality_data(consumer["id"])

        db = self.SessionLocal()
        try:
            design = db.query(models.NailDesign).filter(models.NailDesign.name == "Valid Demand").first()
            completed_tryon = db.query(models.TryOnRecord).filter(
                models.TryOnRecord.nail_design_id == design.id,
                models.TryOnRecord.status == "completed",
            ).first()
            db.add(
                models.Favorite(
                    user_id=consumer["id"],
                    nail_design_id=design.id,
                    try_on_record_id=completed_tryon.id,
                    created_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get(
            "/api/operations/merchant-overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_try_ons"], 1)
        self.assertEqual(body["failed_try_ons"], 1)
        self.assertEqual(body["total_favorites"], 1)
        self.assertEqual(body["conversion_rate"], 100.0)

    def test_merchant_overview_activity_excludes_unfinished_tryons(self):
        _, consumer = self._login("13920001037", "consumer")
        admin_token, _ = self._login("13920001038", "admin")
        self._seed_operations_signal_quality_data(consumer["id"])

        response = self.client.get(
            "/api/operations/merchant-overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        details = [item["detail"] for item in response.json()["recent_activity"]]
        self.assertIn("Valid Demand", details)
        self.assertNotIn("Fallback Demand", details)
        self.assertTrue(any("Failed Noise" in detail for detail in details))
        self.assertNotIn("Processing Noise", details)

    def test_operations_overview_counts_only_completed_tryons_as_business_demand(self):
        _, consumer = self._login("13920001019", "consumer")
        admin_token, _ = self._login("13920001020", "admin")
        self._seed_operations_signal_quality_data(consumer["id"])

        response = self.client.get(
            "/api/operations/overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["today_try_ons"], 1)
        styles = {item["style"]: item["count"] for item in body["trending_styles"]}
        self.assertEqual(styles["valid-style"], 1)
        self.assertNotIn("fallback-style", styles)
        self.assertNotIn("failed-style", styles)
        self.assertNotIn("processing-style", styles)

    def test_operations_overview_counts_utc_inserted_current_day_records(self):
        _, consumer = self._login("13920001025", "consumer")
        admin_token, _ = self._login("13920001026", "admin")

        db = self.SessionLocal()
        try:
            design = models.NailDesign(
                name="UTC Current Day",
                image_url="/uploads/designs/utc-current-day.jpg",
                style_tags=["utc-style"],
                color_tags=["utc-color"],
                scene_tags=["utc-scene"],
                status="active",
            )
            hand_photo = models.HandPhoto(user_id=consumer["id"], image_url="/uploads/hands/utc-current-day.jpg")
            db.add_all([design, hand_photo])
            db.flush()
            utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
            db.add(
                models.TryOnRecord(
                    user_id=consumer["id"],
                    hand_photo_id=hand_photo.id,
                    nail_design_id=design.id,
                    result_image_url="/uploads/results/utc-current-day.jpg",
                    status="completed",
                    created_at=utc_now,
                    completed_at=utc_now,
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get(
            "/api/operations/overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["today_try_ons"], 1)

    def test_operations_trends_excludes_failed_and_processing_tryons_from_distribution(self):
        _, consumer = self._login("13920001021", "consumer")
        admin_token, _ = self._login("13920001022", "admin")
        self._seed_operations_signal_quality_data(consumer["id"])

        response = self.client.get(
            "/api/operations/trends?days=30",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(sum(item["try_ons"] for item in body["daily_stats"]), 1)
        self.assertEqual(body["style_distribution"]["valid-style"], 1)
        self.assertNotIn("fallback-style", body["style_distribution"])
        self.assertNotIn("failed-style", body["style_distribution"])
        self.assertNotIn("processing-style", body["style_distribution"])
        self.assertEqual(body["color_distribution"]["valid-color"], 1)
        self.assertNotIn("fallback-color", body["color_distribution"])
        self.assertNotIn("failed-color", body["color_distribution"])
        self.assertNotIn("processing-color", body["color_distribution"])

    def test_operations_funnel_counts_only_completed_tryons_as_tryon_stage(self):
        _, consumer = self._login("13920001023", "consumer")
        admin_token, _ = self._login("13920001024", "admin")
        self._seed_operations_signal_quality_data(consumer["id"])

        response = self.client.get(
            "/api/operations/funnel?days=30",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        try_on_stage = body["stages"][1]
        self.assertEqual(try_on_stage["count"], 1)
        self.assertEqual(try_on_stage["conversion_rate"], 0.83)


if __name__ == "__main__":
    unittest.main()
