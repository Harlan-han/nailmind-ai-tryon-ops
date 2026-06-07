import unittest
from datetime import datetime
import os
import tempfile

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import clear_login_codes
from app.database import Base, get_db
from app.main import app


class UserDataIsolationTest(unittest.TestCase):
    def setUp(self):
        clear_login_codes()
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_hand_photo_meta_path = os.environ.get("HAND_PHOTO_META_STATE_PATH")
        os.environ["HAND_PHOTO_META_STATE_PATH"] = os.path.join(self.tempdir.name, "hand_photo_meta.json")
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
        if self.previous_hand_photo_meta_path is None:
            os.environ.pop("HAND_PHOTO_META_STATE_PATH", None)
        else:
            os.environ["HAND_PHOTO_META_STATE_PATH"] = self.previous_hand_photo_meta_path
        self.tempdir.cleanup()

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

    def _seed_completed_tryon(self, user_id: int) -> tuple[int, int]:
        from app import models

        db = self.SessionLocal()
        try:
            hand_photo = models.HandPhoto(user_id=user_id, image_url="/uploads/hands/private-hand.jpg")
            db.add(hand_photo)
            db.flush()

            design = models.NailDesign(
                name="Private Result Design",
                image_url="/uploads/designs/private-design.jpg",
                style_tags=["minimal"],
                color_tags=["nude"],
                scene_tags=["daily"],
                status="active",
            )
            db.add(design)
            db.flush()

            related_design = models.NailDesign(
                name="Related Design",
                image_url="/uploads/designs/related-design.jpg",
                style_tags=["minimal"],
                color_tags=["nude"],
                scene_tags=["daily"],
                status="active",
                is_hot=True,
            )
            db.add(related_design)
            db.flush()

            try_on = models.TryOnRecord(
                user_id=user_id,
                hand_photo_id=hand_photo.id,
                nail_design_id=design.id,
                result_image_url="/uploads/results/private-result.png",
                status="completed",
                completed_at=datetime.now(),
            )
            db.add(try_on)
            db.commit()
            return design.id, try_on.id
        finally:
            db.close()

    def test_hand_photo_presets_can_be_used_as_current_user_profile_once(self):
        token, _user = self._login("13910008101")

        presets_response = self.client.get(
            "/api/users/me/hand-photo-presets",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(presets_response.status_code, 200)
        presets = presets_response.json()
        self.assertGreaterEqual(len(presets), 4)
        self.assertEqual(presets[0]["id"], "official-hand-01")
        self.assertTrue(presets[0]["image_url"].endswith("/uploads/hands/hand_01.jpg"))
        self.assertIn("官方预设", presets[0]["tags"])

        use_response = self.client.post(
            "/api/users/me/hand-photo-presets/official-hand-01/use",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(use_response.status_code, 200)
        created = use_response.json()
        self.assertTrue(created["image_url"].endswith("/uploads/hands/hand_01.jpg"))
        self.assertEqual(created["name"], "官方预设 01")
        self.assertEqual(created["crop_ratio"], "4:5")

        repeat_response = self.client.post(
            "/api/users/me/hand-photo-presets/official-hand-01/use",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(repeat_response.status_code, 200)
        self.assertEqual(repeat_response.json()["id"], created["id"])

        photos_response = self.client.get(
            "/api/users/me/hand-photos",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(photos_response.status_code, 200)
        matching = [photo for photo in photos_response.json() if photo["image_url"] == created["image_url"]]
        self.assertEqual(len(matching), 1)

    def test_hand_photo_preset_rejects_unknown_id_and_requires_auth(self):
        unauthenticated_response = self.client.get("/api/users/me/hand-photo-presets")
        self.assertEqual(unauthenticated_response.status_code, 401)

        token, _user = self._login("13910008102")
        unknown_response = self.client.post(
            "/api/users/me/hand-photo-presets/not-real/use",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(unknown_response.status_code, 404)

    def _seed_signal_tryon(
        self,
        user_id: int,
        status: str = "completed",
        result_image_url: str | None = "/uploads/results/signal-result.png",
        design_status: str = "active",
    ) -> tuple[int, int]:
        from app import models

        db = self.SessionLocal()
        try:
            hand_photo = models.HandPhoto(user_id=user_id, image_url="/uploads/hands/signal-hand.jpg")
            db.add(hand_photo)
            db.flush()

            design = models.NailDesign(
                name="Signal Integrity Design",
                image_url="/uploads/designs/signal-design.jpg",
                style_tags=["minimal"],
                color_tags=["nude"],
                scene_tags=["daily"],
                status=design_status,
                favorite_count=0,
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

    def test_tryon_result_requires_owner_or_operator(self):
        owner_token, owner = self._login("13930001001")
        other_token, _ = self._login("13930001002")
        admin_token, _ = self._login("13930001003", "admin")
        _, try_on_id = self._seed_completed_tryon(owner["id"])

        unauthenticated = self.client.get(f"/api/tryon/{try_on_id}")
        other_user = self.client.get(
            f"/api/tryon/{try_on_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        owner_response = self.client.get(
            f"/api/tryon/{try_on_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        admin_response = self.client.get(
            f"/api/tryon/{try_on_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(other_user.status_code, 403)
        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(admin_response.status_code, 200)

    def test_tryon_progress_requires_owner_or_operator(self):
        owner_token, owner = self._login("13930001004")
        other_token, _ = self._login("13930001005")
        _, try_on_id = self._seed_completed_tryon(owner["id"])

        unauthenticated = self.client.get(f"/api/tryon/{try_on_id}/progress")
        other_user = self.client.get(
            f"/api/tryon/{try_on_id}/progress",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        owner_response = self.client.get(
            f"/api/tryon/{try_on_id}/progress",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(other_user.status_code, 403)
        self.assertEqual(owner_response.status_code, 200)

    def test_tryon_recommendations_require_owner_or_operator(self):
        owner_token, owner = self._login("13930001006")
        other_token, _ = self._login("13930001007")
        _, try_on_id = self._seed_completed_tryon(owner["id"])
        payload = {"try_on_id": try_on_id, "limit": 4}

        unauthenticated = self.client.post("/api/recommendations/similar", json=payload)
        other_user = self.client.post(
            "/api/recommendations/similar",
            json=payload,
            headers={"Authorization": f"Bearer {other_token}"},
        )
        owner_response = self.client.post(
            "/api/recommendations/similar",
            json=payload,
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(other_user.status_code, 403)
        self.assertEqual(owner_response.status_code, 200)

    def test_user_profile_lookup_requires_owner_or_operator(self):
        owner_token, owner = self._login("13930001008")
        other_token, _ = self._login("13930001009")
        admin_token, _ = self._login("13930001010", "admin")

        unauthenticated_by_id = self.client.get(f"/api/users/{owner['id']}")
        unauthenticated_by_phone = self.client.get(f"/api/users/phone/{owner['phone']}")
        other_by_id = self.client.get(
            f"/api/users/{owner['id']}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        other_by_phone = self.client.get(
            f"/api/users/phone/{owner['phone']}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        owner_response = self.client.get(
            f"/api/users/{owner['id']}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        admin_response = self.client.get(
            f"/api/users/phone/{owner['phone']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(unauthenticated_by_id.status_code, 401)
        self.assertEqual(unauthenticated_by_phone.status_code, 401)
        self.assertEqual(other_by_id.status_code, 403)
        self.assertEqual(other_by_phone.status_code, 403)
        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(admin_response.status_code, 200)

    def test_hand_photo_routes_require_owner_or_operator(self):
        owner_token, owner = self._login("13930001011")
        other_token, _ = self._login("13930001012")
        admin_token, _ = self._login("13930001013", "admin")
        payload = {"image_url": "/uploads/hands/private-hand.jpg"}

        unauthenticated_create = self.client.post(f"/api/users/{owner['id']}/hand-photos", json=payload)
        other_create = self.client.post(
            f"/api/users/{owner['id']}/hand-photos",
            json=payload,
            headers={"Authorization": f"Bearer {other_token}"},
        )
        owner_create = self.client.post(
            f"/api/users/{owner['id']}/hand-photos",
            json=payload,
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        unauthenticated_list = self.client.get(f"/api/users/{owner['id']}/hand-photos")
        other_list = self.client.get(
            f"/api/users/{owner['id']}/hand-photos",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        admin_list = self.client.get(
            f"/api/users/{owner['id']}/hand-photos",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(unauthenticated_create.status_code, 401)
        self.assertEqual(other_create.status_code, 403)
        self.assertEqual(owner_create.status_code, 200)
        self.assertEqual(unauthenticated_list.status_code, 401)
        self.assertEqual(other_list.status_code, 403)
        self.assertEqual(admin_list.status_code, 200)
        self.assertEqual(len(admin_list.json()), 1)

    def test_hand_photo_profile_metadata_is_persisted_for_current_user(self):
        owner_token, _ = self._login("13930001014")
        headers = {"Authorization": f"Bearer {owner_token}"}
        created = self.client.post(
            "/api/users/me/hand-photos",
            json={"image_url": "/uploads/hands/profile-hand.jpg"},
            headers=headers,
        ).json()

        update_response = self.client.patch(
            f"/api/users/me/hand-photos/{created['id']}",
            json={"name": "右手自然光", "crop_ratio": "4:5"},
            headers=headers,
        )
        list_response = self.client.get("/api/users/me/hand-photos", headers=headers)

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["name"], "右手自然光")
        self.assertEqual(update_response.json()["crop_ratio"], "4:5")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()[0]["name"], "右手自然光")
        self.assertEqual(list_response.json()[0]["crop_ratio"], "4:5")

    def test_hand_photo_profile_delete_archives_photo_for_current_user(self):
        owner_token, _ = self._login("13930001015")
        headers = {"Authorization": f"Bearer {owner_token}"}
        created = self.client.post(
            "/api/users/me/hand-photos",
            json={"image_url": "/uploads/hands/archive-hand.jpg"},
            headers=headers,
        ).json()

        delete_response = self.client.delete(f"/api/users/me/hand-photos/{created['id']}", headers=headers)
        list_response = self.client.get("/api/users/me/hand-photos", headers=headers)

        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["status"], "deleted")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json(), [])

    def test_hand_photo_profile_management_rejects_other_users(self):
        owner_token, _ = self._login("13930001016")
        other_token, _ = self._login("13930001017")
        created = self.client.post(
            "/api/users/me/hand-photos",
            json={"image_url": "/uploads/hands/owner-hand.jpg"},
            headers={"Authorization": f"Bearer {owner_token}"},
        ).json()

        update_response = self.client.patch(
            f"/api/users/me/hand-photos/{created['id']}",
            json={"name": "不该成功"},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        delete_response = self.client.delete(
            f"/api/users/me/hand-photos/{created['id']}",
            headers={"Authorization": f"Bearer {other_token}"},
        )

        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)

    def test_my_preferences_use_only_completed_real_behavior_and_weight_bookings(self):
        from app import models

        token, user = self._login("13930001018")
        db = self.SessionLocal()
        try:
            hand_photo = models.HandPhoto(user_id=user["id"], image_url="/uploads/hands/pref-hand.jpg")
            db.add(hand_photo)
            db.flush()

            booked_design = models.NailDesign(
                name="预约法式款",
                image_url="/uploads/designs/pref-booked.jpg",
                style_tags=["法式"],
                color_tags=["裸色"],
                scene_tags=["约会"],
                status="active",
            )
            failed_design = models.NailDesign(
                name="失败黑色款",
                image_url="/uploads/designs/pref-failed.jpg",
                style_tags=["黑色系"],
                color_tags=["黑色"],
                scene_tags=["派对"],
                status="active",
            )
            db.add_all([booked_design, failed_design])
            db.flush()

            completed = models.TryOnRecord(
                user_id=user["id"],
                hand_photo_id=hand_photo.id,
                nail_design_id=booked_design.id,
                result_image_url="/uploads/results/pref-booked.png",
                status="completed",
                is_candidate=True,
                has_booking_intent=True,
                completed_at=datetime.now(),
            )
            failed = models.TryOnRecord(
                user_id=user["id"],
                hand_photo_id=hand_photo.id,
                nail_design_id=failed_design.id,
                status="failed",
            )
            db.add_all([completed, failed])
            db.flush()
            db.add(
                models.BookingIntent(
                    user_id=user["id"],
                    try_on_record_id=completed.id,
                    nail_design_id=booked_design.id,
                    phone="13930001018",
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/preferences/me", headers={"Authorization": f"Bearer {token}"})
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["total_try_ons"], 1)
        self.assertEqual(payload["total_candidates"], 1)
        self.assertEqual(payload["total_bookings"], 1)
        self.assertEqual(payload["preferred_styles"][0]["name"], "法式")
        self.assertNotIn("黑色系", [item["name"] for item in payload["preferred_styles"]])

    def test_my_preferences_reuses_existing_profile_without_unique_constraint_error(self):
        from app import models

        token, user = self._login("13930001028")
        db = self.SessionLocal()
        try:
            db.add(models.UserPreference(user_id=user["id"], preferred_styles=[]))
            db.commit()
        finally:
            db.close()

        first_response = self.client.get("/api/preferences/me", headers={"Authorization": f"Bearer {token}"})
        second_response = self.client.get("/api/preferences/me/recommendations", headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)

    def test_my_preferences_recovers_from_concurrent_profile_creation(self):
        from sqlalchemy import event
        from sqlalchemy.orm import Session as OrmSession
        from app import models

        token, user = self._login("13930001029")
        inserted_concurrent_profile = False

        def insert_concurrent_profile(session, _flush_context, _instances):
            nonlocal inserted_concurrent_profile
            if inserted_concurrent_profile:
                return
            if not any(
                isinstance(item, models.UserPreference) and item.user_id == user["id"]
                for item in session.new
            ):
                return
            inserted_concurrent_profile = True
            concurrent_db = self.SessionLocal()
            try:
                concurrent_db.add(models.UserPreference(user_id=user["id"], preferred_styles=[]))
                concurrent_db.commit()
            finally:
                concurrent_db.close()

        event.listen(OrmSession, "before_flush", insert_concurrent_profile)
        try:
            response = self.client.get("/api/preferences/me", headers={"Authorization": f"Bearer {token}"})
        finally:
            event.remove(OrmSession, "before_flush", insert_concurrent_profile)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(inserted_concurrent_profile)

    def test_my_recommendations_exclude_already_tried_designs(self):
        from app import models

        token, user = self._login("13930001019")
        db = self.SessionLocal()
        try:
            hand_photo = models.HandPhoto(user_id=user["id"], image_url="/uploads/hands/rec-hand.jpg")
            db.add(hand_photo)
            db.flush()

            tried_design = models.NailDesign(
                name="已试戴法式款",
                image_url="/uploads/designs/rec-tried.jpg",
                style_tags=["法式"],
                color_tags=["裸色"],
                scene_tags=["日常"],
                status="active",
            )
            fresh_design = models.NailDesign(
                name="新推荐法式款",
                image_url="/uploads/designs/rec-fresh.jpg",
                style_tags=["法式"],
                color_tags=["裸色"],
                scene_tags=["约会"],
                status="active",
            )
            db.add_all([tried_design, fresh_design])
            db.flush()
            db.add(
                models.TryOnRecord(
                    user_id=user["id"],
                    hand_photo_id=hand_photo.id,
                    nail_design_id=tried_design.id,
                    result_image_url="/uploads/results/rec-tried.png",
                    status="completed",
                    is_candidate=True,
                    completed_at=datetime.now(),
                )
            )
            db.commit()
            tried_design_id = tried_design.id
            fresh_design_id = fresh_design.id
        finally:
            db.close()

        response = self.client.get("/api/preferences/me/recommendations", headers={"Authorization": f"Bearer {token}"})
        recommended_ids = [item["design"]["id"] for item in response.json()["recommendations"]]

        self.assertEqual(response.status_code, 200)
        self.assertIn(fresh_design_id, recommended_ids)
        self.assertNotIn(tried_design_id, recommended_ids)

    def test_my_candidate_tryons_are_not_hidden_by_recent_record_limit(self):
        from app import models

        token, user = self._login("13930001020")
        db = self.SessionLocal()
        try:
            hand_photo = models.HandPhoto(user_id=user["id"], image_url="/uploads/hands/candidate-hand.jpg")
            db.add(hand_photo)
            db.flush()

            design = models.NailDesign(
                name="深层候选款",
                image_url="/uploads/designs/deep-candidate.jpg",
                style_tags=["法式"],
                color_tags=["裸色"],
                scene_tags=["约会"],
                status="active",
            )
            db.add(design)
            db.flush()

            old_candidate = models.TryOnRecord(
                user_id=user["id"],
                hand_photo_id=hand_photo.id,
                nail_design_id=design.id,
                result_image_url="/uploads/results/deep-candidate.png",
                status="completed",
                is_candidate=True,
                created_at=datetime(2026, 1, 1, 9, 0, 0),
                completed_at=datetime(2026, 1, 1, 9, 1, 0),
            )
            db.add(old_candidate)

            for index in range(25):
                db.add(
                    models.TryOnRecord(
                        user_id=user["id"],
                        hand_photo_id=hand_photo.id,
                        nail_design_id=design.id,
                        result_image_url=f"/uploads/results/recent-{index}.png",
                        status="completed",
                        is_candidate=False,
                        created_at=datetime(2026, 1, 2, 9, index, 0),
                        completed_at=datetime(2026, 1, 2, 9, index, 30),
                    )
                )
            db.commit()
            candidate_id = old_candidate.id
        finally:
            db.close()

        records_response = self.client.get("/api/tryon/me/records", headers={"Authorization": f"Bearer {token}"})
        candidates_response = self.client.get("/api/tryon/me/candidates", headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(records_response.status_code, 200)
        self.assertNotIn(candidate_id, [record["id"] for record in records_response.json()])
        self.assertEqual(candidates_response.status_code, 200)
        self.assertEqual([record["id"] for record in candidates_response.json()], [candidate_id])

    def test_tryon_favorite_creates_removable_favorite_signal(self):
        from app import models

        token, user = self._login("13930001021")
        design_id, try_on_id = self._seed_signal_tryon(user["id"])
        headers = {"Authorization": f"Bearer {token}"}

        first_response = self.client.post(f"/api/tryon/{try_on_id}/favorite", headers=headers)
        db = self.SessionLocal()
        try:
            favorite_count_after_add = db.query(models.Favorite).filter(
                models.Favorite.user_id == user["id"],
                models.Favorite.nail_design_id == design_id,
            ).count()
            try_on_after_add = db.query(models.TryOnRecord).filter(models.TryOnRecord.id == try_on_id).first()
            design_after_add = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
        finally:
            db.close()

        second_response = self.client.post(f"/api/tryon/{try_on_id}/favorite", headers=headers)
        db = self.SessionLocal()
        try:
            favorite_count_after_remove = db.query(models.Favorite).filter(
                models.Favorite.user_id == user["id"],
                models.Favorite.nail_design_id == design_id,
            ).count()
            try_on_after_remove = db.query(models.TryOnRecord).filter(models.TryOnRecord.id == try_on_id).first()
            design_after_remove = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
        finally:
            db.close()

        self.assertEqual(first_response.status_code, 200)
        self.assertTrue(first_response.json()["is_favorite"])
        self.assertEqual(favorite_count_after_add, 1)
        self.assertTrue(try_on_after_add.is_favorite)
        self.assertEqual(design_after_add.favorite_count, 1)
        self.assertEqual(second_response.status_code, 200)
        self.assertFalse(second_response.json()["is_favorite"])
        self.assertEqual(favorite_count_after_remove, 0)
        self.assertFalse(try_on_after_remove.is_favorite)
        self.assertEqual(design_after_remove.favorite_count, 0)

    def test_tryon_intent_signals_require_ready_result(self):
        from app import models

        token, user = self._login("13930001022")
        design_id, try_on_id = self._seed_signal_tryon(
            user["id"],
            status="processing",
            result_image_url=None,
        )
        headers = {"Authorization": f"Bearer {token}"}

        favorite_response = self.client.post(f"/api/tryon/{try_on_id}/favorite", headers=headers)
        candidate_response = self.client.post(f"/api/tryon/{try_on_id}/candidate", headers=headers)

        db = self.SessionLocal()
        try:
            favorite_count = db.query(models.Favorite).filter(
                models.Favorite.user_id == user["id"],
                models.Favorite.nail_design_id == design_id,
            ).count()
            try_on = db.query(models.TryOnRecord).filter(models.TryOnRecord.id == try_on_id).first()
            design = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
        finally:
            db.close()

        self.assertEqual(favorite_response.status_code, 400)
        self.assertEqual(candidate_response.status_code, 400)
        self.assertEqual(favorite_count, 0)
        self.assertFalse(try_on.is_favorite)
        self.assertFalse(try_on.is_candidate)
        self.assertEqual(design.favorite_count, 0)

    def test_tryon_creation_rejects_archived_photo_or_inactive_design(self):
        from app import models

        token, user = self._login("13930001027")
        headers = {"Authorization": f"Bearer {token}"}

        db = self.SessionLocal()
        try:
            archived_photo = models.HandPhoto(
                user_id=user["id"],
                image_url="/uploads/hands/archived-hand.jpg",
                status="deleted",
            )
            active_photo = models.HandPhoto(
                user_id=user["id"],
                image_url="/uploads/hands/active-hand.jpg",
                status="active",
            )
            active_design = models.NailDesign(
                name="Active Try-on Design",
                image_url="/uploads/designs/active-tryon.jpg",
                status="active",
            )
            inactive_design = models.NailDesign(
                name="Inactive Try-on Design",
                image_url="/uploads/designs/inactive-tryon.jpg",
                status="inactive",
            )
            db.add_all([archived_photo, active_photo, active_design, inactive_design])
            db.commit()
            archived_photo_id = archived_photo.id
            active_photo_id = active_photo.id
            active_design_id = active_design.id
            inactive_design_id = inactive_design.id
        finally:
            db.close()

        archived_photo_response = self.client.post(
            "/api/tryon/",
            json={"hand_photo_id": archived_photo_id, "nail_design_id": active_design_id},
            headers=headers,
        )
        inactive_design_response = self.client.post(
            "/api/tryon/",
            json={"hand_photo_id": active_photo_id, "nail_design_id": inactive_design_id},
            headers=headers,
        )

        self.assertEqual(archived_photo_response.status_code, 404)
        self.assertEqual(inactive_design_response.status_code, 404)

    def test_tryon_intent_signals_require_active_design(self):
        from app import models

        token, user = self._login("13930001028")
        design_id, try_on_id = self._seed_signal_tryon(
            user["id"],
            design_status="inactive",
        )
        headers = {"Authorization": f"Bearer {token}"}

        favorite_response = self.client.post(f"/api/tryon/{try_on_id}/favorite", headers=headers)
        candidate_response = self.client.post(f"/api/tryon/{try_on_id}/candidate", headers=headers)
        favorite_api_response = self.client.post(
            "/api/favorites/",
            json={"nail_design_id": design_id, "try_on_record_id": try_on_id},
            headers=headers,
        )

        db = self.SessionLocal()
        try:
            favorite_count = db.query(models.Favorite).filter(
                models.Favorite.user_id == user["id"],
                models.Favorite.nail_design_id == design_id,
            ).count()
            try_on = db.query(models.TryOnRecord).filter(models.TryOnRecord.id == try_on_id).first()
        finally:
            db.close()

        self.assertEqual(favorite_response.status_code, 404)
        self.assertEqual(candidate_response.status_code, 404)
        self.assertEqual(favorite_api_response.status_code, 404)
        self.assertEqual(favorite_count, 0)
        self.assertFalse(try_on.is_favorite)
        self.assertFalse(try_on.is_candidate)

    def test_operator_cannot_write_user_intent_signals(self):
        from app import models

        _, owner = self._login("13930001023")
        admin_token, _ = self._login("13930001024", "admin")
        design_id, try_on_id = self._seed_signal_tryon(owner["id"])
        headers = {"Authorization": f"Bearer {admin_token}"}

        favorite_response = self.client.post(f"/api/tryon/{try_on_id}/favorite", headers=headers)
        candidate_response = self.client.post(f"/api/tryon/{try_on_id}/candidate", headers=headers)

        db = self.SessionLocal()
        try:
            favorite_count = db.query(models.Favorite).filter(
                models.Favorite.user_id == owner["id"],
                models.Favorite.nail_design_id == design_id,
            ).count()
            try_on = db.query(models.TryOnRecord).filter(models.TryOnRecord.id == try_on_id).first()
        finally:
            db.close()

        self.assertEqual(favorite_response.status_code, 403)
        self.assertEqual(candidate_response.status_code, 403)
        self.assertEqual(favorite_count, 0)
        self.assertFalse(try_on.is_favorite)
        self.assertFalse(try_on.is_candidate)

    def test_favorites_api_rejects_invalid_or_mismatched_signal_source(self):
        from app import models

        token, user = self._login("13930001025")
        design_id, try_on_id = self._seed_signal_tryon(user["id"])
        _, pending_try_on_id = self._seed_signal_tryon(
            user["id"],
            status="processing",
            result_image_url=None,
        )
        headers = {"Authorization": f"Bearer {token}"}

        db = self.SessionLocal()
        try:
            other_design = models.NailDesign(
                name="Other Signal Design",
                image_url="/uploads/designs/other-signal.jpg",
                status="active",
            )
            db.add(other_design)
            db.commit()
            other_design_id = other_design.id
        finally:
            db.close()

        missing_design = self.client.post(
            "/api/favorites/",
            json={"nail_design_id": 99999},
            headers=headers,
        )
        mismatched_try_on = self.client.post(
            "/api/favorites/",
            json={"nail_design_id": other_design_id, "try_on_record_id": try_on_id},
            headers=headers,
        )
        unfinished_try_on = self.client.post(
            "/api/favorites/",
            json={"nail_design_id": design_id, "try_on_record_id": pending_try_on_id},
            headers=headers,
        )

        db = self.SessionLocal()
        try:
            favorite_count = db.query(models.Favorite).filter(
                models.Favorite.user_id == user["id"],
            ).count()
        finally:
            db.close()

        self.assertEqual(missing_design.status_code, 404)
        self.assertEqual(mismatched_try_on.status_code, 400)
        self.assertEqual(unfinished_try_on.status_code, 400)
        self.assertEqual(favorite_count, 0)

    def test_favorites_api_syncs_tryon_favorite_signal(self):
        from app import models

        token, user = self._login("13930001026")
        design_id, try_on_id = self._seed_signal_tryon(user["id"])
        headers = {"Authorization": f"Bearer {token}"}

        create_response = self.client.post(
            "/api/favorites/",
            json={"nail_design_id": design_id, "try_on_record_id": try_on_id},
            headers=headers,
        )
        favorite_id = create_response.json()["id"] if create_response.status_code == 200 else None
        remove_response = self.client.delete(
            f"/api/favorites/{favorite_id}",
            headers=headers,
        )

        db = self.SessionLocal()
        try:
            favorite_count = db.query(models.Favorite).filter(
                models.Favorite.user_id == user["id"],
                models.Favorite.nail_design_id == design_id,
            ).count()
            try_on = db.query(models.TryOnRecord).filter(models.TryOnRecord.id == try_on_id).first()
            design = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
        finally:
            db.close()

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(remove_response.status_code, 200)
        self.assertEqual(favorite_count, 0)
        self.assertFalse(try_on.is_favorite)
        self.assertEqual(design.favorite_count, 0)


if __name__ == "__main__":
    unittest.main()
