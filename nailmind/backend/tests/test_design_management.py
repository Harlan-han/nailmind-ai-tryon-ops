import unittest
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import clear_login_codes
from app.database import Base, get_db
from app.main import app


class DesignManagementContractTest(unittest.TestCase):
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

    def _login(self, phone: str, user_type: str = "consumer") -> str:
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
        return login_response.json()["access_token"]

    def test_operator_design_list_includes_inactive_designs(self):
        from app import models

        token = self._login("13931000001", "admin")
        db = self.SessionLocal()
        try:
            db.add_all([
                models.NailDesign(
                    name="Active Admin Design",
                    image_url="/uploads/designs/active-admin.jpg",
                    status="active",
                ),
                models.NailDesign(
                    name="Inactive Admin Design",
                    image_url="/uploads/designs/inactive-admin.jpg",
                    status="inactive",
                ),
            ])
            db.commit()
        finally:
            db.close()

        response = self.client.get(
            "/api/designs/?include_inactive=true&limit=100",
            headers={"Authorization": f"Bearer {token}"},
        )
        statuses = {item["name"]: item["status"] for item in response.json()}

        self.assertEqual(response.status_code, 200)
        self.assertEqual(statuses["Active Admin Design"], "active")
        self.assertEqual(statuses["Inactive Admin Design"], "inactive")

    def test_operator_design_asset_view_excludes_missing_and_duplicate_covers(self):
        from app import models

        token = self._login("13931000004", "admin")
        db = self.SessionLocal()
        try:
            db.add_all([
                models.NailDesign(
                    name="Official Asset Owner",
                    image_url="/uploads/designs/design_01.jpg",
                    status="active",
                ),
                models.NailDesign(
                    name="Missing Cover Asset",
                    image_url="/uploads/designs/ops-hot.png",
                    status="active",
                ),
                models.NailDesign(
                    name="Duplicate Cover Asset",
                    image_url="/uploads/designs/design_01.jpg",
                    status="active",
                    try_on_count=999,
                ),
            ])
            db.commit()
        finally:
            db.close()

        response = self.client.get(
            "/api/designs/?include_inactive=true&only_servable=true&dedupe_images=true&limit=100",
            headers={"Authorization": f"Bearer {token}"},
        )
        names = [item["name"] for item in response.json()]
        image_urls = [item["image_url"] for item in response.json()]

        self.assertEqual(response.status_code, 200)
        self.assertIn("Official Asset Owner", names)
        self.assertNotIn("Missing Cover Asset", names)
        self.assertNotIn("Duplicate Cover Asset", names)
        self.assertEqual(image_urls.count("/uploads/designs/design_01.jpg"), 1)

    def test_operator_design_list_without_trailing_slash_does_not_redirect(self):
        from app import models

        token = self._login("13931000005", "admin")
        db = self.SessionLocal()
        try:
            db.add(
                models.NailDesign(
                    name="No Redirect Admin Design",
                    image_url="/uploads/designs/design_01.jpg",
                    status="active",
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get(
            "/api/designs?include_inactive=true&only_servable=true&dedupe_images=true&limit=100",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["name"], "No Redirect Admin Design")

    def test_public_design_list_remains_open_but_excludes_inactive_designs(self):
        from app import models

        db = self.SessionLocal()
        try:
            db.add_all([
                models.NailDesign(
                    name="Public Active Design",
                    image_url="/uploads/designs/design_01.jpg",
                    status="active",
                ),
                models.NailDesign(
                    name="Public Inactive Design",
                    image_url="/uploads/designs/design_02.jpg",
                    status="inactive",
                ),
            ])
            db.commit()
        finally:
            db.close()

        public_response = self.client.get("/api/designs/?limit=100")
        inactive_response = self.client.get("/api/designs/?include_inactive=true&limit=100")
        names = [item["name"] for item in public_response.json()]

        self.assertEqual(public_response.status_code, 200)
        self.assertIn("Public Active Design", names)
        self.assertNotIn("Public Inactive Design", names)
        self.assertEqual(inactive_response.status_code, 403)

    def test_public_design_list_excludes_missing_local_cover(self):
        from app import models

        db = self.SessionLocal()
        try:
            db.add_all([
                models.NailDesign(
                    name="Missing Local Cover Design",
                    image_url="/uploads/designs/ops-hot.png",
                    status="active",
                ),
                models.NailDesign(
                    name="Existing Local Cover Design",
                    image_url="/uploads/designs/design_01.jpg",
                    status="active",
                ),
            ])
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/designs/?limit=100")
        names = [item["name"] for item in response.json()]

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Missing Local Cover Design", names)
        self.assertIn("Existing Local Cover Design", names)

    def test_public_hot_designs_exclude_missing_local_cover(self):
        from app import models

        db = self.SessionLocal()
        try:
            db.add_all([
                models.NailDesign(
                    name="Missing Hot Cover Design",
                    image_url="/uploads/designs/ops-hot.png",
                    status="active",
                    is_hot=True,
                ),
                models.NailDesign(
                    name="Existing Hot Cover Design",
                    image_url="/uploads/designs/design_01.jpg",
                    status="active",
                    is_hot=True,
                ),
            ])
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/designs/hot?limit=10")
        names = [item["name"] for item in response.json()]

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Missing Hot Cover Design", names)
        self.assertIn("Existing Hot Cover Design", names)

    def test_public_design_list_deduplicates_reused_local_cover(self):
        from app import models

        db = self.SessionLocal()
        try:
            db.add_all([
                models.NailDesign(
                    name="Official Cover Owner",
                    image_url="/uploads/designs/design_01.jpg",
                    status="active",
                    try_on_count=1,
                ),
                models.NailDesign(
                    name="Duplicate Cover Pollution",
                    image_url="/uploads/designs/design_01.jpg",
                    status="active",
                    try_on_count=999,
                ),
            ])
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/designs/?limit=100")
        names = [item["name"] for item in response.json()]
        image_urls = [item["image_url"] for item in response.json()]

        self.assertEqual(response.status_code, 200)
        self.assertIn("Official Cover Owner", names)
        self.assertNotIn("Duplicate Cover Pollution", names)
        self.assertEqual(image_urls.count("/uploads/designs/design_01.jpg"), 1)

    def test_public_hot_designs_deduplicates_reused_local_cover(self):
        from app import models

        db = self.SessionLocal()
        try:
            db.add_all([
                models.NailDesign(
                    name="Official Hot Cover Owner",
                    image_url="/uploads/designs/design_01.jpg",
                    status="active",
                    is_hot=True,
                    try_on_count=1,
                ),
                models.NailDesign(
                    name="Duplicate Hot Cover Pollution",
                    image_url="/uploads/designs/design_01.jpg",
                    status="active",
                    is_hot=True,
                    try_on_count=999,
                ),
            ])
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/designs/hot?limit=10")
        names = [item["name"] for item in response.json()]
        image_urls = [item["image_url"] for item in response.json()]

        self.assertEqual(response.status_code, 200)
        self.assertIn("Official Hot Cover Owner", names)
        self.assertNotIn("Duplicate Hot Cover Pollution", names)
        self.assertEqual(image_urls.count("/uploads/designs/design_01.jpg"), 1)

    def test_public_hot_designs_are_ranked_by_completed_tryon_signals_not_stale_counters(self):
        from app import models

        db = self.SessionLocal()
        try:
            user = models.User(phone="13931000998", nickname="Hot Ranking User")
            db.add(user)
            db.flush()
            hand_photo = models.HandPhoto(user_id=user.id, image_url="/uploads/hands/hot-ranking-hand.jpg")
            db.add(hand_photo)
            db.flush()

            stale_hot = models.NailDesign(
                name="Stale Failed Hot",
                image_url="/uploads/designs/design_01.jpg",
                status="active",
                is_hot=True,
                try_on_count=99,
            )
            real_hot = models.NailDesign(
                name="Real Completed Hot",
                image_url="/uploads/designs/design_02.jpg",
                status="active",
                is_hot=True,
                try_on_count=1,
            )
            db.add_all([stale_hot, real_hot])
            db.flush()

            now = datetime.now()
            for index in range(6):
                db.add(
                    models.TryOnRecord(
                        user_id=user.id,
                        hand_photo_id=hand_photo.id,
                        nail_design_id=real_hot.id,
                        result_image_url=f"/uploads/results/real-hot-ranking-{index}.png",
                        status="completed",
                        created_at=now - timedelta(minutes=index),
                        completed_at=now - timedelta(minutes=index),
                    )
                )
            for index in range(8):
                db.add(
                    models.TryOnRecord(
                        user_id=user.id,
                        hand_photo_id=hand_photo.id,
                        nail_design_id=stale_hot.id,
                        status="failed",
                        created_at=now - timedelta(minutes=index),
                        completed_at=now - timedelta(minutes=index),
                    )
                )
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/designs/hot?limit=2")

        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in response.json()]
        self.assertEqual(names[:2], ["Real Completed Hot", "Stale Failed Hot"])

    def test_public_trending_designs_are_ranked_by_completed_tryon_signals(self):
        from app import models

        db = self.SessionLocal()
        try:
            user = models.User(phone="13931000997", nickname="Trending Ranking User")
            db.add(user)
            db.flush()
            hand_photo = models.HandPhoto(user_id=user.id, image_url="/uploads/hands/trending-ranking-hand.jpg")
            db.add(hand_photo)
            db.flush()

            stale_trending = models.NailDesign(
                name="Stale Failed Trending",
                image_url="/uploads/designs/design_03.jpg",
                status="active",
                try_on_count=120,
                favorite_count=0,
            )
            real_trending = models.NailDesign(
                name="Real Completed Trending",
                image_url="/uploads/designs/design_04.jpg",
                status="active",
                try_on_count=2,
                favorite_count=0,
            )
            db.add_all([stale_trending, real_trending])
            db.flush()

            now = datetime.now()
            for index in range(5):
                db.add(
                    models.TryOnRecord(
                        user_id=user.id,
                        hand_photo_id=hand_photo.id,
                        nail_design_id=real_trending.id,
                        result_image_url=f"/uploads/results/real-trending-{index}.png",
                        status="completed",
                        created_at=now - timedelta(minutes=index),
                        completed_at=now - timedelta(minutes=index),
                    )
                )
            for index in range(9):
                db.add(
                    models.TryOnRecord(
                        user_id=user.id,
                        hand_photo_id=hand_photo.id,
                        nail_design_id=stale_trending.id,
                        status="failed",
                        created_at=now - timedelta(minutes=index),
                        completed_at=now - timedelta(minutes=index),
                    )
                )
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/recommendations/trending?limit=2")

        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in response.json()]
        self.assertEqual(names[:2], ["Real Completed Trending", "Stale Failed Trending"])

    def test_design_delete_archives_without_breaking_historical_tryon(self):
        from app import models

        token = self._login("13931000002", "admin")
        db = self.SessionLocal()
        try:
            user = models.User(phone="13931000999", nickname="Historical User")
            db.add(user)
            db.flush()
            hand_photo = models.HandPhoto(user_id=user.id, image_url="/uploads/hands/history-hand.jpg")
            design = models.NailDesign(
                name="Historical Linked Design",
                image_url="/uploads/designs/history-design.jpg",
                status="active",
            )
            db.add_all([hand_photo, design])
            db.flush()
            try_on = models.TryOnRecord(
                user_id=user.id,
                hand_photo_id=hand_photo.id,
                nail_design_id=design.id,
                result_image_url="/uploads/results/history-result.png",
                status="completed",
            )
            db.add(try_on)
            db.commit()
            design_id = design.id
            try_on_id = try_on.id
        finally:
            db.close()

        delete_response = self.client.delete(
            f"/api/designs/{design_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        db = self.SessionLocal()
        try:
            archived_design = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
            linked_try_on = db.query(models.TryOnRecord).filter(models.TryOnRecord.id == try_on_id).first()
        finally:
            db.close()

        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["status"], "inactive")
        self.assertIsNotNone(archived_design)
        self.assertEqual(archived_design.status, "inactive")
        self.assertEqual(linked_try_on.nail_design_id, design_id)

    def test_design_status_update_rejects_unknown_status(self):
        from app import models

        token = self._login("13931000003", "admin")
        db = self.SessionLocal()
        try:
            design = models.NailDesign(
                name="Status Guard Design",
                image_url="/uploads/designs/status-guard.jpg",
                status="active",
            )
            db.add(design)
            db.commit()
            design_id = design.id
        finally:
            db.close()

        response = self.client.patch(
            f"/api/designs/{design_id}/status?status=deleted",
            headers={"Authorization": f"Bearer {token}"},
        )

        db = self.SessionLocal()
        try:
            design = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
        finally:
            db.close()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(design.status, "active")


if __name__ == "__main__":
    unittest.main()
