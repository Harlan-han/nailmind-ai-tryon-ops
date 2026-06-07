from contextlib import contextmanager
from datetime import datetime, timedelta
import os
import tempfile
import unittest
from unittest.mock import patch


class OperationsAgentContractTest(unittest.TestCase):
    def setUp(self):
        try:
            from app.operations_agent.suggestion_store import clear_agent_suggestions
            from app.operations_agent.agent_control import reset_agent_control_state

            clear_agent_suggestions()
            reset_agent_control_state()
        except ModuleNotFoundError:
            pass

    def test_tool_registry_exposes_expected_read_only_tools(self):
        from app.operations_agent.tools import get_tool_definitions

        tool_names = {tool["function"]["name"] for tool in get_tool_definitions()}

        self.assertEqual(
            tool_names,
            {
                "get_overview",
                "get_trends",
                "get_hot_candidates",
                "get_cold_designs",
                "get_funnel",
                "get_ai_insights",
                "get_daily_report",
                "get_weekly_report",
                "get_recommendation_slot_plan",
                "get_action_plan",
                "get_suggestions",
                "get_booking_followups",
                "analyze_design_performance",
                "explain_hot_design",
                "find_high_tryon_low_booking_designs",
                "find_high_favorite_low_booking_designs",
                "find_converted_tryon_images",
            },
        )

    def _create_memory_db(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.database import Base

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(bind=engine)
        return TestingSessionLocal()

    @contextmanager
    def _isolated_app_client(self):
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.database import Base, get_db
        from app.main import app

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        try:
            yield TestClient(app), TestingSessionLocal
        finally:
            app.dependency_overrides.pop(get_db, None)
            engine.dispose()

    def _seed_design_signals(self, db):
        from app import models

        user = models.User(phone="18800000000", nickname="测试用户")
        db.add(user)
        db.flush()

        hand_photo = models.HandPhoto(user_id=user.id, image_url="/uploads/hands/test.png")
        db.add(hand_photo)
        db.flush()

        design = models.NailDesign(
            name="高试戴低预约款",
            image_url="/uploads/designs/test.png",
            style_tags=["法式"],
            color_tags=["裸色"],
            scene_tags=["日常"],
            status="active",
            view_count=100,
        )
        db.add(design)
        db.flush()

        try_on_records = []
        for index in range(10):
            try_on = models.TryOnRecord(
                user_id=user.id,
                hand_photo_id=hand_photo.id,
                nail_design_id=design.id,
                result_image_url=f"/uploads/results/result_{index}.png",
                status="completed",
                is_favorite=index < 4,
                has_booking_intent=index == 0,
            )
            db.add(try_on)
            try_on_records.append(try_on)
        db.flush()

        for try_on in try_on_records[:4]:
            db.add(
                models.Favorite(
                    user_id=user.id,
                    nail_design_id=design.id,
                    try_on_record_id=try_on.id,
                )
            )

        db.add(
            models.BookingIntent(
                user_id=user.id,
                try_on_record_id=try_on_records[0].id,
                nail_design_id=design.id,
                phone="18800000000",
            )
        )
        db.commit()
        return design

    def _seed_report_signals(self, db):
        from app import models

        now = datetime.now()
        user = models.User(phone="18800000001", nickname="周报用户")
        db.add(user)
        db.flush()

        hand_photo = models.HandPhoto(user_id=user.id, image_url="/uploads/hands/report.png")
        db.add(hand_photo)
        db.flush()

        promote_design = models.NailDesign(
            name="高潜推荐款",
            image_url="/uploads/designs/promote.png",
            style_tags=["法式"],
            color_tags=["裸色"],
            scene_tags=["通勤"],
            status="active",
            is_hot=False,
            view_count=160,
        )
        demote_design = models.NailDesign(
            name="低效占位款",
            image_url="/uploads/designs/demote.png",
            style_tags=["猫眼"],
            color_tags=["黑色"],
            scene_tags=["派对"],
            status="active",
            is_hot=True,
            view_count=140,
            try_on_count=2,
            favorite_count=0,
            booking_count=0,
        )
        db.add_all([promote_design, demote_design])
        db.flush()

        promote_try_ons = []
        for index in range(12):
            try_on = models.TryOnRecord(
                user_id=user.id,
                hand_photo_id=hand_photo.id,
                nail_design_id=promote_design.id,
                result_image_url=f"/uploads/results/promote_{index}.png",
                status="completed",
                is_favorite=index < 5,
                has_booking_intent=index < 2,
                created_at=now - timedelta(days=index % 5),
            )
            db.add(try_on)
            promote_try_ons.append(try_on)

        for index in range(2):
            db.add(
                models.TryOnRecord(
                    user_id=user.id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=demote_design.id,
                    result_image_url=f"/uploads/results/demote_{index}.png",
                    status="completed",
                    created_at=now - timedelta(days=index),
                )
            )

        db.flush()

        for try_on in promote_try_ons[:5]:
            db.add(
                models.Favorite(
                    user_id=user.id,
                    nail_design_id=promote_design.id,
                    try_on_record_id=try_on.id,
                    created_at=try_on.created_at,
                )
            )

        for try_on in promote_try_ons[:2]:
            db.add(
                models.BookingIntent(
                    user_id=user.id,
                    try_on_record_id=try_on.id,
                    nail_design_id=promote_design.id,
                    phone="18800000001",
                    created_at=try_on.created_at,
                )
            )

        db.commit()
        return promote_design, demote_design

    def _operator_headers(self, client, phone="13918889999"):
        code = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "运营测试账号", "user_type": "admin"},
        ).json()["debug_code"]
        login_response = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": code, "nickname": "运营测试账号", "user_type": "admin"},
        )
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_design_performance_tool_links_tryon_favorite_booking_signals(self):
        from app.operations_agent.tools import OperationsToolRegistry

        db = self._create_memory_db()
        design = self._seed_design_signals(db)

        result = OperationsToolRegistry().execute(
            "analyze_design_performance",
            {"design_id": design.id},
            db,
        )

        data = result["data"]
        self.assertEqual(data["design"]["id"], design.id)
        self.assertEqual(data["signals"]["try_on_count"], 10)
        self.assertEqual(data["signals"]["favorite_count"], 4)
        self.assertEqual(data["signals"]["booking_count"], 1)
        self.assertEqual(data["rates"]["try_on_to_booking_rate"], 10.0)
        self.assertEqual(data["converted_try_on_images"][0]["result_image_url"], "/uploads/results/result_0.png")

    def test_design_performance_tool_excludes_failed_tryons_from_recent_business_signals(self):
        from app import models
        from app.operations_agent.tools import OperationsToolRegistry

        db = self._create_memory_db()
        user = models.User(phone="18800000009", nickname="Signal User")
        db.add(user)
        db.flush()

        hand_photo = models.HandPhoto(user_id=user.id, image_url="/uploads/hands/signal-tool.png")
        db.add(hand_photo)
        db.flush()

        design = models.NailDesign(
            name="Signal Quality Design",
            image_url="/uploads/designs/signal-tool.png",
            style_tags=["signal"],
            color_tags=["red"],
            scene_tags=["daily"],
            status="active",
            view_count=80,
        )
        db.add(design)
        db.flush()

        now = datetime.now()
        db.add_all(
            [
                models.TryOnRecord(
                    user_id=user.id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=design.id,
                    result_image_url="/uploads/results/signal-completed.png",
                    status="completed",
                    created_at=now - timedelta(days=1),
                    completed_at=now - timedelta(days=1),
                ),
                models.TryOnRecord(
                    user_id=user.id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=design.id,
                    result_image_url="/uploads/results/signal-fallback.png",
                    status="fallback_completed",
                    created_at=now - timedelta(days=2),
                    completed_at=now - timedelta(days=2),
                ),
                models.TryOnRecord(
                    user_id=user.id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=design.id,
                    status="failed",
                    created_at=now - timedelta(days=3),
                    completed_at=now - timedelta(days=3),
                ),
                models.TryOnRecord(
                    user_id=user.id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=design.id,
                    status="processing",
                    created_at=now - timedelta(days=4),
                ),
            ]
        )
        db.commit()

        result = OperationsToolRegistry().execute(
            "analyze_design_performance",
            {"design_id": design.id},
            db,
        )

        self.assertEqual(result["data"]["signals"]["try_on_count"], 1)
        self.assertEqual(result["data"]["signals"]["recent_7d_try_on_count"], 1)

    def test_design_performance_tool_uses_effective_visual_tags(self):
        from app import models
        from app.operations_agent.tools import OperationsToolRegistry

        db = self._create_memory_db()
        design = models.NailDesign(
            name="款式 20",
            image_url="/uploads/designs/design_20.jpg",
            style_tags=["爱心", "可爱"],
            color_tags=["粉色"],
            scene_tags=["约会"],
            status="active",
        )
        db.add(design)
        db.commit()

        result = OperationsToolRegistry().execute(
            "analyze_design_performance",
            {"design_id": design.id},
            db,
        )

        self.assertIn("奶牛纹", result["data"]["design"]["style_tags"])
        self.assertIn("银色", result["data"]["design"]["color_tags"])
        self.assertNotIn("爱心", result["data"]["design"]["style_tags"])

    def test_high_tryon_low_booking_tool_flags_conversion_gap(self):
        from app.operations_agent.tools import OperationsToolRegistry

        db = self._create_memory_db()
        design = self._seed_design_signals(db)

        result = OperationsToolRegistry().execute(
            "find_high_tryon_low_booking_designs",
            {"limit": 3},
            db,
        )

        items = result["data"]["items"]
        self.assertEqual(items[0]["design"]["id"], design.id)
        self.assertEqual(items[0]["alert_type"], "high_tryon_low_booking")

    def test_booking_followups_tool_returns_pending_customer_queue(self):
        from app.operations_agent.tools import OperationsToolRegistry

        db = self._create_memory_db()
        design = self._seed_design_signals(db)

        result = OperationsToolRegistry().execute(
            "get_booking_followups",
            {"status": "pending", "limit": 5},
            db,
        )

        item = result["data"]["items"][0]
        self.assertEqual(item["design_name"], design.name)
        self.assertEqual(item["status"], "pending")
        self.assertEqual(item["phone"], "18800000000")

    def test_ai_predictions_ignore_failed_and_processing_tryons(self):
        from app import models
        from app.ai_agent import AIOperationsAgent

        db = self._create_memory_db()
        user = models.User(phone="18800000011", nickname="Prediction Noise User")
        db.add(user)
        db.flush()
        hand_photo = models.HandPhoto(user_id=user.id, image_url="/uploads/hands/prediction-noise.png")
        design = models.NailDesign(
            name="Prediction Noise Design",
            image_url="/uploads/designs/prediction-noise.png",
            style_tags=["噪声风格"],
            status="active",
        )
        db.add_all([hand_photo, design])
        db.flush()

        now = datetime.now()
        for index in range(8):
            db.add(
                models.TryOnRecord(
                    user_id=user.id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=design.id,
                    status="failed" if index % 2 == 0 else "processing",
                    created_at=now - timedelta(days=index),
                    completed_at=now - timedelta(days=index) if index % 2 == 0 else None,
                )
            )
        db.commit()

        prediction = AIOperationsAgent(db).predict_trend(7)

        self.assertEqual(prediction["trend_direction"], "insufficient_data")
        self.assertIsNone(prediction["prediction"])

    def test_ai_emerging_styles_ignore_failed_and_processing_tryons(self):
        from app import models
        from app.ai_agent import AIOperationsAgent

        db = self._create_memory_db()
        user = models.User(phone="18800000012", nickname="Emerging Noise User")
        db.add(user)
        db.flush()
        hand_photo = models.HandPhoto(user_id=user.id, image_url="/uploads/hands/emerging-noise.png")
        failed_design = models.NailDesign(
            name="Failed Emerging Noise",
            image_url="/uploads/designs/emerging-noise.png",
            style_tags=["失败噪声"],
            status="active",
        )
        completed_design = models.NailDesign(
            name="Real Emerging Signal",
            image_url="/uploads/designs/real-emerging.png",
            style_tags=["真实趋势"],
            status="active",
        )
        db.add_all([hand_photo, failed_design, completed_design])
        db.flush()

        now = datetime.now()
        for index in range(6):
            db.add(
                models.TryOnRecord(
                    user_id=user.id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=failed_design.id,
                    status="failed" if index % 2 == 0 else "processing",
                    created_at=now - timedelta(days=index),
                    completed_at=now - timedelta(days=index) if index % 2 == 0 else None,
                )
            )
            db.add(
                models.TryOnRecord(
                    user_id=user.id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=completed_design.id,
                    result_image_url=f"/uploads/results/real-emerging-{index}.png",
                    status="completed",
                    is_favorite=index < 2,
                    created_at=now - timedelta(days=index),
                    completed_at=now - timedelta(days=index),
                )
            )
        db.commit()

        styles = AIOperationsAgent(db).identify_emerging_styles(14)
        style_names = {item["style"] for item in styles}

        self.assertIn("真实趋势", style_names)
        self.assertNotIn("失败噪声", style_names)

    def test_inventory_recommendations_ignore_designs_without_servable_images(self):
        from app import models
        from app.ai_agent import AIOperationsAgent

        db = self._create_memory_db()
        visible_design = models.NailDesign(
            name="官方真实图款式",
            image_url="/uploads/designs/design_01.jpg",
            status="active",
            try_on_count=60,
            favorite_count=30,
            booking_count=12,
        )
        missing_image_design = models.NailDesign(
            name="缺图运营测试款",
            image_url="/uploads/designs/not-found-for-inventory.png",
            status="active",
            try_on_count=90,
            favorite_count=45,
            booking_count=18,
        )
        db.add_all([visible_design, missing_image_design])
        db.commit()

        recommendations = AIOperationsAgent(db).generate_inventory_recommendations()
        recommended_names = {item["design_name"] for item in recommendations}

        self.assertIn(visible_design.name, recommended_names)
        self.assertNotIn(missing_image_design.name, recommended_names)

    def test_consumer_assistant_recommends_designs_and_exposes_operator_insights(self):
        from app import models

        with self._isolated_app_client() as (client, SessionLocal):
            db = SessionLocal()
            user = models.User(phone="13966000001", nickname="小鹿", user_type="consumer")
            admin = models.User(phone="13966000002", nickname="运营", user_type="admin")
            design = models.NailDesign(
                name="显白法式款",
                image_url="/uploads/designs/design_01.jpg",
                style_tags=["法式", "裸感"],
                color_tags=["裸色"],
                scene_tags=["通勤"],
                status="active",
                is_hot=True,
                try_on_count=42,
                favorite_count=12,
            )
            db.add_all([user, admin, design])
            db.commit()
            db.close()

            user_code = client.post(
                "/api/auth/request-code",
                json={"phone": "13966000001", "nickname": "小鹿", "user_type": "consumer"},
            ).json()["debug_code"]
            user_token = client.post(
                "/api/auth/login",
                json={"phone": "13966000001", "nickname": "小鹿", "user_type": "consumer", "code": user_code},
            ).json()["access_token"]

            response = client.post(
                "/api/consumer-assistant/chat",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"message": "我想要通勤显白一点"},
            )
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["persona"], "小甲灵")
            self.assertGreaterEqual(len(body["recommendations"]), 1)

            admin_code = client.post(
                "/api/auth/request-code",
                json={"phone": "13966000002", "nickname": "运营", "user_type": "admin"},
            ).json()["debug_code"]
            admin_token = client.post(
                "/api/auth/login",
                json={"phone": "13966000002", "nickname": "运营", "user_type": "admin", "code": admin_code},
            ).json()["access_token"]
            insights = client.get(
                "/api/consumer-assistant/insights",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            self.assertEqual(insights.status_code, 200)
            self.assertGreaterEqual(insights.json()["total_messages"], 1)
            self.assertIn("小鹿", [item["user_name"] for item in insights.json()["recent_messages"]])

    def test_consumer_assistant_ranks_designs_by_prompt_tags_before_hotness(self):
        from app import models
        from app.routers.consumer_assistant import _pick_recommendations

        with self._isolated_app_client() as (_client, SessionLocal):
            db = SessionLocal()
            commute_short = models.NailDesign(
                name="通勤短甲裸感款",
                image_url="/uploads/designs/design_01.jpg",
                style_tags=["裸感", "极简"],
                color_tags=["裸色"],
                scene_tags=["通勤", "日常"],
                length="短甲",
                shape="圆形",
                status="active",
                is_hot=False,
                try_on_count=3,
                favorite_count=1,
            )
            date_sweet = models.NailDesign(
                name="约会甜美爱心款",
                image_url="/uploads/designs/design_25.jpg",
                style_tags=["法式", "爱心", "甜美"],
                color_tags=["红色", "粉色"],
                scene_tags=["约会", "节日"],
                length="中长甲",
                shape="方圆形",
                status="active",
                is_hot=True,
                try_on_count=180,
                favorite_count=90,
            )
            party_black = models.NailDesign(
                name="派对黑色星星款",
                image_url="/uploads/designs/design_09.jpg",
                style_tags=["黑色系", "星星", "手绘"],
                color_tags=["黑色"],
                scene_tags=["派对", "甜酷"],
                length="中长甲",
                shape="方圆形",
                status="active",
                is_hot=True,
                try_on_count=160,
                favorite_count=70,
            )
            db.add_all([commute_short, date_sweet, party_black])
            db.commit()

            commute_results = _pick_recommendations(db, "只想要短甲，越自然越好", limit=2)
            date_results = _pick_recommendations(db, "周末约会想要甜美爱心一点", limit=2)

            self.assertEqual(commute_results[0]["name"], "通勤短甲裸感款")
            self.assertEqual(date_results[0]["name"], "约会甜美爱心款")
            self.assertNotEqual(
                [item["id"] for item in commute_results],
                [item["id"] for item in date_results],
            )
            db.close()

    def test_consumer_assistant_insights_has_demo_baseline_when_empty(self):
        from app.routers.consumer_assistant import _RECENT_EVENTS

        _RECENT_EVENTS.clear()
        with self._isolated_app_client() as (client, _SessionLocal):
            headers = self._operator_headers(client, phone="13966000003")

            insights = client.get(
                "/api/consumer-assistant/insights",
                headers=headers,
            )

            self.assertEqual(insights.status_code, 200)
            body = insights.json()
            self.assertGreaterEqual(body["total_messages"], 3)
            self.assertGreaterEqual(body["active_users"], 3)
            self.assertIn("日常通勤", [item["name"] for item in body["top_intents"]])

    def test_today_workbench_generates_action_cards_from_existing_signals(self):
        from app.operations_agent.workbench import build_today_workbench

        db = self._create_memory_db()
        design = self._seed_design_signals(db)

        workbench = build_today_workbench(db)

        self.assertGreaterEqual(workbench["summary"]["pending_booking_count"], 1)
        self.assertGreaterEqual(workbench["summary"]["conversion_gap_count"], 1)
        self.assertGreaterEqual(len(workbench["action_cards"]), 2)
        self.assertEqual(workbench["action_cards"][0]["type"], "booking_followup")
        self.assertIn(design.name, workbench["action_cards"][1]["title"])

    def test_weekly_report_tool_aggregates_existing_behavior_signals(self):
        from app.operations_agent.tools import OperationsToolRegistry

        db = self._create_memory_db()
        promote_design, _demote_design = self._seed_report_signals(db)

        result = OperationsToolRegistry().execute("get_weekly_report", {"days": 7}, db)

        data = result["data"]
        self.assertEqual(data["period_days"], 7)
        self.assertGreaterEqual(data["metrics"]["try_ons"], 12)
        self.assertGreaterEqual(data["metrics"]["bookings"], 2)
        self.assertEqual(data["top_styles"][0]["tag"], "法式")
        self.assertIn(promote_design.name, data["summary"])
        self.assertGreaterEqual(len(data["recommendations"]), 1)

    def test_recommendation_slot_plan_tool_separates_promote_and_demote_actions(self):
        from app.operations_agent.tools import OperationsToolRegistry

        db = self._create_memory_db()
        promote_design, demote_design = self._seed_report_signals(db)

        result = OperationsToolRegistry().execute("get_recommendation_slot_plan", {"limit": 5}, db)

        recommendations = result["data"]["recommendations"]
        slot_actions = {item["slot_action"]: item for item in recommendations}

        self.assertIn("promote", slot_actions)
        self.assertIn("demote", slot_actions)
        self.assertEqual(slot_actions["promote"]["design"]["id"], promote_design.id)
        self.assertEqual(slot_actions["demote"]["design"]["id"], demote_design.id)
        self.assertTrue(all(item["requires_confirmation"] for item in recommendations))

    def test_recommendation_slot_plan_keeps_demote_action_when_limit_is_small(self):
        from app import models
        from app.operations_agent.tools import OperationsToolRegistry

        db = self._create_memory_db()
        self._seed_report_signals(db)
        user = db.query(models.User).first()
        hand_photo = db.query(models.HandPhoto).first()
        now = datetime.now()

        second_promote = models.NailDesign(
            name="第二高潜推荐款",
            image_url="/uploads/designs/promote-2.png",
            style_tags=["渐变"],
            color_tags=["粉色"],
            scene_tags=["约会"],
            status="active",
            is_hot=False,
            view_count=180,
        )
        db.add(second_promote)
        db.flush()

        for index in range(9):
            db.add(
                models.TryOnRecord(
                    user_id=user.id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=second_promote.id,
                    result_image_url=f"/uploads/results/promote_2_{index}.png",
                    status="completed",
                    created_at=now - timedelta(days=index % 4),
                )
            )
        db.commit()

        result = OperationsToolRegistry().execute("get_recommendation_slot_plan", {"limit": 2}, db)

        slot_actions = [item["slot_action"] for item in result["data"]["recommendations"]]
        self.assertEqual(len(slot_actions), 2)
        self.assertIn("promote", slot_actions)
        self.assertIn("demote", slot_actions)

    def test_missing_api_key_returns_rule_based_response(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeTools:
            def __init__(self):
                self.calls = []

            def execute(self, name, arguments, db):
                self.calls.append((name, arguments))
                return {"tool": name, "data": {"today_try_ons": 12}}

        runner = OperationsAgentRunner(llm_client=None, tools=FakeTools())
        response = runner.chat(
            message="今天最该推哪几个款？",
            db=None,
            context={"days": 7},
        )

        self.assertTrue(response.answer)
        self.assertGreaterEqual(len(response.tool_trace), 1)
        self.assertGreaterEqual(len(response.recommended_actions), 1)

    def test_tool_summary_turns_raw_metrics_into_evidence_and_actions(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeTools:
            def __init__(self):
                self.calls = []

            def execute(self, name, arguments, db):
                self.calls.append((name, arguments))
                if name == "get_overview":
                    return {
                        "tool": name,
                        "data": {
                            "today_try_ons": 12,
                            "today_favorites": 5,
                            "today_booking_intents": 2,
                            "hot_designs_count": 6,
                            "trending_styles": [{"style": "法式", "count": 8}],
                        },
                    }
                if name == "get_action_plan":
                    return {
                        "tool": name,
                        "data": {
                            "actions": [
                                {
                                    "title": "上调法式款推荐位",
                                    "description": "法式今日试戴领先",
                                    "priority": "high",
                                }
                            ]
                        },
                    }
                return {"tool": name, "data": {}}

        runner = OperationsAgentRunner(llm_client=None, tools=FakeTools())
        response = runner.chat("今天怎么运营？", db=None, context={})

        evidence_values = " ".join(item.value for item in response.evidence)
        action_titles = [action.title for action in response.recommended_actions]

        self.assertIn("今日试戴 12", evidence_values)
        self.assertIn("今日预约 2", evidence_values)
        self.assertIn("法式", evidence_values)
        self.assertIn("上调法式款推荐位", action_titles)

    def test_rule_based_fallback_routes_weekly_report_to_weekly_tool(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeTools:
            def __init__(self):
                self.calls = []

            def execute(self, name, arguments, db):
                self.calls.append((name, arguments))
                return {
                    "tool": name,
                    "data": {
                        "summary": "本周运营周报",
                        "recommendations": [
                            {
                                "action": "复盘本周高潜款",
                                "reason": "本周试戴增长",
                                "priority": "medium",
                            }
                        ],
                    },
                }

        tools = FakeTools()
        response = OperationsAgentRunner(llm_client=None, tools=tools).chat("生成本周运营周报", db=None, context={})

        self.assertEqual(tools.calls[0], ("get_weekly_report", {"days": 7}))
        self.assertEqual(response.tool_trace[0].tool, "get_weekly_report")
        self.assertGreaterEqual(len(response.evidence), 1)
        self.assertGreaterEqual(len(response.recommended_actions), 1)

    def test_rule_based_fallback_routes_recommendation_slot_plan_to_slot_tool(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeTools:
            def __init__(self):
                self.calls = []

            def execute(self, name, arguments, db):
                self.calls.append((name, arguments))
                return {
                    "tool": name,
                    "data": {
                        "summary": "推荐位调整建议",
                        "recommendations": [
                            {
                                "action": "上调高潜款推荐位",
                                "reason": "试戴高且转化稳定",
                                "priority": "high",
                            }
                        ],
                    },
                }

        tools = FakeTools()
        response = OperationsAgentRunner(llm_client=None, tools=tools).chat("生成推荐位调整建议", db=None, context={})

        self.assertEqual(tools.calls[0], ("get_recommendation_slot_plan", {"limit": 5}))
        self.assertEqual(response.tool_trace[0].tool, "get_recommendation_slot_plan")
        self.assertGreaterEqual(len(response.evidence), 1)
        self.assertGreaterEqual(len(response.recommended_actions), 1)

    def test_rule_based_fallback_routes_conversion_gap_questions_to_data_loop_tools(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeTools:
            def __init__(self):
                self.calls = []

            def execute(self, name, arguments, db):
                self.calls.append((name, arguments))
                return {"tool": name, "data": {"items": []}}

        tools = FakeTools()
        runner = OperationsAgentRunner(llm_client=None, tools=tools)
        runner.chat("哪些款试戴高但预约低？", db=None, context={"days": 30})

        self.assertEqual(tools.calls[0][0], "find_high_tryon_low_booking_designs")

    def test_rule_based_fallback_routes_booking_followup_questions_to_followup_tool(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeTools:
            def __init__(self):
                self.calls = []

            def execute(self, name, arguments, db):
                self.calls.append((name, arguments))
                return {"tool": name, "data": {"items": []}}

        tools = FakeTools()
        runner = OperationsAgentRunner(llm_client=None, tools=tools)
        runner.chat("今天哪些预约客户需要优先跟进？", db=None, context={})

        self.assertEqual(tools.calls[0][0], "get_booking_followups")

    def test_rule_based_fallback_routes_design_id_questions_to_design_diagnosis(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeTools:
            def __init__(self):
                self.calls = []

            def execute(self, name, arguments, db):
                self.calls.append((name, arguments))
                return {"tool": name, "data": {"design": {"id": arguments.get("design_id")}}}

        tools = FakeTools()
        runner = OperationsAgentRunner(llm_client=None, tools=tools)
        runner.chat("分析款式 12 为什么热？", db=None, context={})

        self.assertEqual(tools.calls[0], ("explain_hot_design", {"design_id": 12}))

    def test_runner_sends_tools_on_follow_up_after_tool_result(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeLlmClient:
            available = True

            def __init__(self):
                self.calls = []

            def create_chat_completion(self, messages, tools=None, tool_choice=None, **kwargs):
                self.calls.append({"messages": messages, "tools": tools, "tool_choice": tool_choice, **kwargs})
                if len(self.calls) == 1:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {
                                                "name": "get_hot_candidates",
                                                "arguments": '{"limit": 3}',
                                            },
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": '{"answer":"建议优先推广潜力款。","evidence":[],"recommended_actions":[],"confidence":"medium"}',
                            }
                        }
                    ]
                }

        class FakeTools:
            def execute(self, name, arguments, db):
                return {"tool": name, "data": {"items": []}}

        llm = FakeLlmClient()
        runner = OperationsAgentRunner(llm_client=llm, tools=FakeTools())
        runner.chat("今天最该推哪几个款？", db=None, context={"days": 30})

        self.assertIsNotNone(llm.calls[0]["tools"])
        self.assertIsNotNone(llm.calls[1]["tools"])

    def test_runner_parses_deepseek_json_wrapped_in_markdown_fence(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeLlmClient:
            available = True

            def __init__(self):
                self.calls = []

            def create_chat_completion(self, messages, tools=None, tool_choice=None, **kwargs):
                self.calls.append({"messages": messages, "tools": tools, "tool_choice": tool_choice, **kwargs})
                if len(self.calls) == 1:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {
                                                "name": "find_high_tryon_low_booking_designs",
                                                "arguments": '{"limit": 3}',
                                            },
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": '```json\n{"answer":"已找到转化断层款。","evidence":[{"label":"试戴高预约低","value":"款式 1 试戴 20 次预约 0 次","source":"find_high_tryon_low_booking_designs"}],"recommended_actions":[{"title":"优化预约入口","reason":"试戴兴趣没有转化为预约","priority":"high","requires_confirmation":true}],"confidence":"high"}\n```',
                            }
                        }
                    ]
                }

        class FakeTools:
            def execute(self, name, arguments, db):
                return {"tool": name, "data": {"items": []}}

        runner = OperationsAgentRunner(llm_client=FakeLlmClient(), tools=FakeTools())
        response = runner.chat("哪些款试戴高但预约低？", db=None, context={})

        self.assertEqual(response.answer, "已找到转化断层款。")
        self.assertEqual(response.evidence[0].source, "find_high_tryon_low_booking_designs")
        self.assertEqual(response.recommended_actions[0].title, "优化预约入口")

    def test_runner_parses_json_embedded_after_model_preface(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeLlmClient:
            available = True

            def __init__(self):
                self.calls = []

            def create_chat_completion(self, messages, tools=None, tool_choice=None, **kwargs):
                self.calls.append({"messages": messages, "tools": tools, "tool_choice": tool_choice, **kwargs})
                if len(self.calls) == 1:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {"name": "get_ai_insights", "arguments": "{}"},
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": '下面是结构化结果：\\n{"answer":"今天有异常。","evidence":[],"recommended_actions":[],"confidence":"high"}\\n请人工确认。',
                            }
                        }
                    ]
                }

        class FakeTools:
            def execute(self, name, arguments, db):
                return {"tool": name, "data": {}}

        runner = OperationsAgentRunner(llm_client=FakeLlmClient(), tools=FakeTools())
        response = runner.chat("今天有什么异常？", db=None, context={})

        self.assertEqual(response.answer, "今天有异常。")
        self.assertEqual(response.confidence, "high")

    def test_runner_falls_back_to_tool_summary_when_final_json_parse_fails(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeLlmClient:
            available = True

            def __init__(self):
                self.calls = []

            def create_chat_completion(self, messages, tools=None, tool_choice=None, **kwargs):
                self.calls.append({"messages": messages, "tools": tools, "tool_choice": tool_choice, **kwargs})
                if len(self.calls) == 1:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {"name": "get_ai_insights", "arguments": "{}"},
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "我看了一下，今天有异常，但我没有按 JSON 输出。",
                            }
                        }
                    ]
                }

        class FakeTools:
            def execute(self, name, arguments, db):
                return {"tool": name, "data": {"alerts": ["试戴量低于昨日"]}}

        runner = OperationsAgentRunner(llm_client=FakeLlmClient(), tools=FakeTools())
        response = runner.chat("今天有什么异常？", db=None, context={})

        self.assertNotIn("结构化解析失败", response.answer)
        self.assertGreaterEqual(len(response.evidence), 1)
        self.assertGreaterEqual(len(response.recommended_actions), 1)
        self.assertTrue(any(trace.tool == "deepseek_parse" and trace.status == "failed" for trace in response.tool_trace))
        self.assertEqual(response.confidence, "low")

    def test_runner_repairs_non_json_final_response_before_tool_fallback(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeLlmClient:
            available = True

            def __init__(self):
                self.calls = []

            def create_chat_completion(self, messages, tools=None, tool_choice=None, **kwargs):
                self.calls.append({"messages": messages, "tools": tools, "tool_choice": tool_choice, **kwargs})
                if len(self.calls) == 1:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {"name": "get_ai_insights", "arguments": "{}"},
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                if len(self.calls) == 2:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": "今天有异常：试戴量为 0，需要检查数据链路。",
                                }
                            }
                        ]
                    }
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": '{"answer":"今天有异常：试戴量为 0，需要检查数据链路。","evidence":[{"label":"异常","value":"试戴量为 0","source":"get_ai_insights"}],"recommended_actions":[{"title":"检查试戴埋点和任务状态","reason":"核心行为数据为 0","priority":"high","requires_confirmation":true}],"confidence":"medium"}',
                            }
                        }
                    ]
                }

        class FakeTools:
            def execute(self, name, arguments, db):
                return {"tool": name, "data": {"alerts": ["试戴量为 0"]}}

        llm = FakeLlmClient()
        runner = OperationsAgentRunner(llm_client=llm, tools=FakeTools())
        response = runner.chat("今天有什么异常？", db=None, context={})

        self.assertEqual(response.answer, "今天有异常：试戴量为 0，需要检查数据链路。")
        self.assertEqual(response.evidence[0].source, "get_ai_insights")
        self.assertEqual(response.recommended_actions[0].priority, "high")
        self.assertTrue(any(trace.tool == "deepseek_parse" and trace.status == "success" for trace in response.tool_trace))
        self.assertEqual(len(llm.calls), 3)

    def test_runner_uses_tool_summary_when_final_deepseek_call_fails(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeLlmClient:
            available = True

            def __init__(self):
                self.calls = []

            def create_chat_completion(self, messages, tools=None, tool_choice=None, **kwargs):
                self.calls.append({"messages": messages, "tools": tools, "tool_choice": tool_choice, **kwargs})
                if len(self.calls) == 1:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {"name": "get_daily_report", "arguments": "{}"},
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                raise RuntimeError("DeepSeek temporary failure")

        class FakeTools:
            def execute(self, name, arguments, db):
                return {"tool": name, "data": {"summary": "今日试戴 0 次"}}

        runner = OperationsAgentRunner(llm_client=FakeLlmClient(), tools=FakeTools())
        response = runner.chat("生成今日运营日报", db=None, context={})

        self.assertTrue(response.answer)
        self.assertGreaterEqual(len(response.evidence), 1)
        self.assertEqual(response.tool_trace[0].tool, "get_daily_report")
        self.assertEqual(response.tool_trace[0].status, "success")
        self.assertFalse(any(trace.tool == "deepseek" and trace.status == "failed" for trace in response.tool_trace))
        self.assertTrue(any(trace.tool == "deepseek_summary" and trace.status == "fallback" for trace in response.tool_trace))
        self.assertEqual(response.confidence, "low")

    def test_runner_uses_tool_fallback_when_initial_deepseek_call_fails(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeLlmClient:
            available = True

            def create_chat_completion(self, *args, **kwargs):
                raise RuntimeError("DeepSeek authentication failed")

        class FakeTools:
            def execute(self, name, arguments, db):
                return {"tool": name, "data": {"summary": "今日试戴 0 次"}}

        runner = OperationsAgentRunner(llm_client=FakeLlmClient(), tools=FakeTools())
        response = runner.chat("生成今日运营日报", db=None, context={})

        self.assertTrue(response.answer)
        self.assertGreaterEqual(len(response.evidence), 1)
        self.assertFalse(any(trace.tool == "deepseek" and trace.status == "failed" for trace in response.tool_trace))
        self.assertTrue(any(trace.tool == "deepseek" and trace.status == "fallback" for trace in response.tool_trace))
        self.assertEqual(response.confidence, "low")

    def test_runner_requests_json_object_for_final_llm_response(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeLlmClient:
            available = True

            def __init__(self):
                self.calls = []

            def create_chat_completion(self, messages, tools=None, tool_choice=None, **kwargs):
                self.calls.append({"messages": messages, "tools": tools, "tool_choice": tool_choice, **kwargs})
                if len(self.calls) == 1:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {"name": "get_overview", "arguments": "{}"},
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": '{"answer":"已分析。","evidence":[],"recommended_actions":[],"confidence":"medium"}',
                            }
                        }
                    ]
                }

        class FakeTools:
            def execute(self, name, arguments, db):
                return {"tool": name, "data": {}}

        llm = FakeLlmClient()
        runner = OperationsAgentRunner(llm_client=llm, tools=FakeTools())
        runner.chat("看一下今天运营情况", db=None, context={})

        self.assertEqual(llm.calls[1]["response_format"], {"type": "json_object"})
        self.assertEqual(llm.calls[1]["tool_choice"], "none")
        self.assertEqual(llm.calls[1]["max_tokens"], 4096)

    def test_runner_replies_to_every_tool_call_id(self):
        from app.operations_agent.runner import OperationsAgentRunner

        class FakeLlmClient:
            available = True

            def __init__(self):
                self.calls = []

            def create_chat_completion(self, messages, tools=None, tool_choice=None, **kwargs):
                self.calls.append({"messages": messages, "tools": tools, "tool_choice": tool_choice, **kwargs})
                if len(self.calls) == 1:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {"name": "get_overview", "arguments": "{}"},
                                        },
                                        {
                                            "id": "call_2",
                                            "type": "function",
                                            "function": {"name": "get_trends", "arguments": "{}"},
                                        },
                                        {
                                            "id": "call_3",
                                            "type": "function",
                                            "function": {"name": "get_funnel", "arguments": "{}"},
                                        },
                                        {
                                            "id": "call_4",
                                            "type": "function",
                                            "function": {"name": "get_action_plan", "arguments": "{}"},
                                        },
                                        {
                                            "id": "call_5",
                                            "type": "function",
                                            "function": {"name": "get_suggestions", "arguments": "{}"},
                                        },
                                    ],
                                }
                            }
                        ]
                    }
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": '{"answer":"已分析。","evidence":[],"recommended_actions":[],"confidence":"medium"}',
                            }
                        }
                    ]
                }

        class FakeTools:
            def execute(self, name, arguments, db):
                return {"tool": name, "data": {}}

        llm = FakeLlmClient()
        runner = OperationsAgentRunner(llm_client=llm, tools=FakeTools())
        runner.chat("看一下今天运营情况", db=None, context={})

        follow_up_messages = llm.calls[1]["messages"]
        tool_message_ids = [
            message["tool_call_id"]
            for message in follow_up_messages
            if message.get("role") == "tool"
        ]

        self.assertEqual(tool_message_ids, ["call_1", "call_2", "call_3", "call_4", "call_5"])

    def test_agent_actions_can_be_synced_to_suggestions(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        headers = self._operator_headers(client, phone="13918889991")

        payload = {
            "source_message": "今天最该推哪 3 个款？",
            "answer": "建议重点推广款式 01。",
            "evidence": [
                {
                    "label": "试戴量",
                    "value": "款式 01 今日试戴最高",
                    "source": "get_hot_candidates",
                }
            ],
            "actions": [
                {
                    "title": "重点推广款式 01",
                    "reason": "试戴量和收藏转化领先",
                    "priority": "high",
                    "risk": "需要确认库存和接待能力",
                    "requires_confirmation": True,
                }
            ],
        }

        response = client.post("/api/operations/assistant/suggestions", json=payload, headers=headers)

        self.assertEqual(response.status_code, 200)
        saved = response.json()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["type"], "agent")
        self.assertEqual(saved[0]["status"], "pending")
        self.assertIn("款式 01", saved[0]["title"])

        suggestions = client.get("/api/operations/suggestions", headers=headers).json()
        self.assertTrue(any(item["id"] == saved[0]["id"] for item in suggestions))

    def test_operator_suggestions_reject_unbounded_limit(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        headers = self._operator_headers(client, phone="13918889990")

        zero_response = client.get("/api/operations/suggestions?limit=0", headers=headers)
        negative_response = client.get("/api/operations/suggestions?limit=-1", headers=headers)

        self.assertEqual(zero_response.status_code, 422)
        self.assertEqual(negative_response.status_code, 422)

    def test_agent_synced_suggestion_status_can_be_updated(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        headers = self._operator_headers(client, phone="13918889992")
        saved = client.post(
            "/api/operations/assistant/suggestions",
            json={
                "actions": [
                    {
                        "title": "调整推荐位",
                        "reason": "低转化款需要下推荐",
                        "priority": "medium",
                        "requires_confirmation": True,
                    }
                ]
            },
            headers=headers,
        ).json()

        suggestion_id = saved[0]["id"]
        accept_response = client.post(f"/api/operations/suggestions/{suggestion_id}/accept", headers=headers)
        suggestions = client.get("/api/operations/suggestions?status=accepted", headers=headers).json()

        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(accept_response.json()["status"], "accepted")
        self.assertTrue(any(item["id"] == suggestion_id for item in suggestions))

    def test_dynamic_suggestions_use_completed_tryons_instead_of_stale_counters(self):
        from app import models
        from app.routers import operations

        db = self._create_memory_db()
        user = models.User(phone="18800000010", nickname="Suggestion Signal User")
        db.add(user)
        db.flush()

        hand_photo = models.HandPhoto(user_id=user.id, image_url="/uploads/hands/suggestion-signal.png")
        db.add(hand_photo)
        db.flush()

        false_hot = models.NailDesign(
            name="Failed Counter Noise",
            image_url="/uploads/designs/failed-counter-noise.png",
            style_tags=["noise"],
            color_tags=["gray"],
            scene_tags=["daily"],
            status="active",
            is_hot=False,
            try_on_count=24,
            favorite_count=0,
        )
        real_hot = models.NailDesign(
            name="Completed Demand Signal",
            image_url="/uploads/designs/completed-demand-signal.png",
            style_tags=["signal"],
            color_tags=["red"],
            scene_tags=["party"],
            status="active",
            is_hot=False,
            try_on_count=0,
            favorite_count=4,
        )
        db.add_all([false_hot, real_hot])
        db.flush()

        now = datetime.now()
        for index in range(24):
            db.add(
                models.TryOnRecord(
                    user_id=user.id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=false_hot.id,
                    status="failed",
                    created_at=now - timedelta(hours=index % 24),
                    completed_at=now - timedelta(hours=index % 24),
                )
            )
        for index in range(20):
            db.add(
                models.TryOnRecord(
                    user_id=user.id,
                    hand_photo_id=hand_photo.id,
                    nail_design_id=real_hot.id,
                    result_image_url=f"/uploads/results/real-hot-{index}.png",
                    status="completed",
                    created_at=now - timedelta(hours=index % 24),
                    completed_at=now - timedelta(hours=index % 24),
                )
            )
        db.commit()

        suggestions = operations.get_suggestions(db=db)
        hot_suggestion_ids = {item["id"] for item in suggestions if item["type"] == "hot"}

        self.assertIn(f"hot_{real_hot.id}", hot_suggestion_ids)
        self.assertNotIn(f"hot_{false_hot.id}", hot_suggestion_ids)

    def test_accepting_hot_suggestion_updates_user_facing_hot_designs(self):
        from app import models

        with self._isolated_app_client() as (client, SessionLocal):
            headers = self._operator_headers(client, phone="13918889994")

            db = SessionLocal()
            try:
                design = models.NailDesign(
                    name="Operational Hot Candidate",
                    image_url="/uploads/designs/design_05.jpg",
                    style_tags=["chrome"],
                    color_tags=["red"],
                    scene_tags=["party"],
                    status="active",
                    is_hot=False,
                    try_on_count=24,
                    favorite_count=8,
                )
                db.add(design)
                db.commit()
                design_id = design.id
            finally:
                db.close()

            accept_response = client.post(f"/api/operations/suggestions/hot_{design_id}/accept", headers=headers)
            hot_response = client.get("/api/designs/hot", headers=headers)

        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(accept_response.json()["status"], "accepted")
        self.assertEqual(accept_response.json()["applied_action"], "promote_hot_design")
        self.assertTrue(any(item["id"] == design_id for item in hot_response.json()))

    def test_accepting_cold_suggestion_removes_design_from_user_facing_hot_designs(self):
        from app import models

        with self._isolated_app_client() as (client, SessionLocal):
            headers = self._operator_headers(client, phone="13918889995")

            db = SessionLocal()
            try:
                design = models.NailDesign(
                    name="Operational Cold Candidate",
                    image_url="/uploads/designs/design_06.jpg",
                    style_tags=["cat eye"],
                    color_tags=["black"],
                    scene_tags=["party"],
                    status="active",
                    is_hot=True,
                    try_on_count=2,
                    favorite_count=0,
                )
                db.add(design)
                db.commit()
                design_id = design.id
            finally:
                db.close()

            accept_response = client.post(f"/api/operations/suggestions/cold_{design_id}/accept", headers=headers)
            hot_response = client.get("/api/designs/hot", headers=headers)

        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(accept_response.json()["status"], "accepted")
        self.assertEqual(accept_response.json()["applied_action"], "demote_hot_design")
        self.assertFalse(any(item["id"] == design_id for item in hot_response.json()))

    def test_external_agent_message_reuses_chat_runner_for_mobile_channels(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        headers = self._operator_headers(client, phone="13918889993")
        response = client.post(
            "/api/operations/assistant/external-message",
            json={
                "channel": "feishu",
                "sender": "harlan",
                "message": "生成今日运营日报",
            },
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["channel"], "feishu")
        self.assertTrue(payload["reply_text"])
        self.assertGreaterEqual(len(payload["tool_trace"]), 1)

    def test_agent_capabilities_expose_runtime_features_for_acceptance(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        headers = self._operator_headers(client, phone="13918889995")
        response = client.get("/api/operations/assistant/capabilities", headers=headers)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["version"], "agent-v2")
        self.assertTrue(payload["features"]["structured_evidence"])
        self.assertTrue(payload["features"]["external_webhook"])
        self.assertTrue(payload["features"]["scheduled_daily_report"])
        self.assertIn("feishu", payload["channels"])

    def test_agent_status_exposes_chat_first_gateway_and_schedule_state(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        headers = self._operator_headers(client, phone="13918889996")

        response = client.get("/api/operations/assistant/status", headers=headers)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["runtime"]["entrypoint"], "chat")
        self.assertIn("llm_configured", payload["runtime"])
        self.assertIn("model", payload["runtime"])
        self.assertIn("multi_channel_gateway", payload["openclaw_patterns"])
        self.assertIn("tool_workspace", payload["openclaw_patterns"])
        self.assertIn("safe_action_approval", payload["safety"]["execution_policy"])
        self.assertIn("feishu", payload["channels"])
        self.assertIn("wechat", payload["channels"])
        self.assertIn("qq", payload["channels"])
        self.assertIn("daily_report", payload["scheduled_tasks"])
        self.assertIn("next_run_at", payload["scheduled_tasks"]["daily_report"])
        self.assertIsInstance(payload["recent_deliveries"], list)
        self.assertGreaterEqual(len(payload["suggested_commands"]), 4)
        self.assertIn("gateway", payload)
        self.assertEqual(payload["gateway"]["primary_inbox"], "feishu")
        self.assertIn("/api/operations/assistant/webhook/feishu", payload["gateway"]["webhook_paths"])
        self.assertIn("connectors", payload["gateway"])
        self.assertIn("FEISHU_BOT_WEBHOOK_URL", payload["gateway"]["connectors"]["feishu"]["required_env"])
        self.assertEqual(payload["gateway"]["connectors"]["wechat"]["status"], "simulated")
        self.assertIn("manual_confirmation_required", payload["gateway"]["security"])

    def test_agent_status_exposes_external_setup_playbook_for_operators(self):
        from app.operations_agent.agent_control import get_agent_runtime_status

        payload = get_agent_runtime_status()

        self.assertIn("quick_setup", payload["gateway"])
        self.assertEqual(payload["gateway"]["quick_setup"][0]["channel"], "feishu")
        self.assertIn("/api/operations/assistant/webhook/feishu", payload["gateway"]["quick_setup"][0]["webhook_url"])
        self.assertIn("message_examples", payload["gateway"]["connectors"]["feishu"])
        self.assertIn("生成今日运营日报", payload["gateway"]["connectors"]["feishu"]["message_examples"])
        self.assertIn("automation_playbook", payload)
        self.assertIn("开启日报 09:30", payload["automation_playbook"]["commands"])
        self.assertEqual(
            payload["scheduled_tasks"]["daily_report"]["manual_trigger_path"],
            "/api/operations/assistant/schedules/daily-report/run",
        )

    def test_channel_statuses_describe_inbound_outbound_and_required_env(self):
        from app.operations_agent.agent_control import get_channel_statuses

        statuses = get_channel_statuses()

        self.assertEqual(statuses["feishu"]["inbound"], "webhook")
        self.assertEqual(statuses["feishu"]["outbound"], "bot_webhook")
        self.assertIn("FEISHU_BOT_WEBHOOK_URL", statuses["feishu"]["required_env"])
        self.assertEqual(statuses["wechat"]["inbound"], "generic_webhook")
        self.assertEqual(statuses["wechat"]["outbound"], "mock")
        self.assertEqual(statuses["qq"]["status"], "simulated")

    def test_external_webhook_accepts_generic_mobile_message_in_debug(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/operations/assistant/webhook",
            json={
                "channel": "feishu",
                "sender": "mobile_operator",
                "text": "生成今日运营日报",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["channel"], "feishu")
        self.assertTrue(response.json()["reply_text"])

    def test_external_webhook_requires_configured_token_outside_debug(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        with patch("app.routers.operations.get_settings") as mocked_settings:
            mocked_settings.return_value.DEBUG = False
            mocked_settings.return_value.OPERATIONS_AGENT_EXTERNAL_ENABLED = True
            mocked_settings.return_value.OPERATIONS_AGENT_EXTERNAL_TOKEN = ""
            response = client.post(
                "/api/operations/assistant/webhook",
                json={
                    "channel": "feishu",
                    "sender": "mobile_operator",
                    "text": "生成今日运营日报",
                },
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("token", response.json()["detail"].lower())

    def test_external_webhook_rejects_invalid_token_when_configured(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        with patch("app.routers.operations.get_settings") as mocked_settings:
            mocked_settings.return_value.DEBUG = False
            mocked_settings.return_value.OPERATIONS_AGENT_EXTERNAL_ENABLED = True
            mocked_settings.return_value.OPERATIONS_AGENT_EXTERNAL_TOKEN = "expected-token"
            response = client.post(
                "/api/operations/assistant/webhook",
                headers={"X-Nailmind-Agent-Token": "wrong-token"},
                json={
                    "channel": "feishu",
                    "sender": "mobile_operator",
                    "text": "生成今日运营日报",
                },
            )

        self.assertEqual(response.status_code, 403)

    def test_external_webhook_accepts_valid_header_token_when_configured(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        with patch("app.routers.operations.get_settings") as mocked_settings:
            mocked_settings.return_value.DEBUG = False
            mocked_settings.return_value.OPERATIONS_AGENT_EXTERNAL_ENABLED = True
            mocked_settings.return_value.OPERATIONS_AGENT_EXTERNAL_TOKEN = "expected-token"
            response = client.post(
                "/api/operations/assistant/webhook",
                headers={"X-Nailmind-Agent-Token": "expected-token"},
                json={
                    "channel": "feishu",
                    "sender": "mobile_operator",
                    "text": "生成今日运营日报",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["channel"], "feishu")
        self.assertTrue(response.json()["reply_text"])

    def test_agent_daily_report_schedule_can_be_configured_and_triggered(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        headers = self._operator_headers(client, phone="13918889994")
        config_response = client.put(
            "/api/operations/assistant/schedules/daily-report",
            json={
                "enabled": True,
                "time": "09:30",
                "channels": ["feishu"],
                "prompt": "生成今日运营日报",
            },
            headers=headers,
        )
        trigger_response = client.post("/api/operations/assistant/schedules/daily-report/run", headers=headers)
        status_response = client.get("/api/operations/assistant/schedules", headers=headers)

        self.assertEqual(config_response.status_code, 200)
        self.assertTrue(config_response.json()["enabled"])
        self.assertEqual(trigger_response.status_code, 200)
        triggered = trigger_response.json()
        self.assertEqual(triggered["task"], "daily-report")
        self.assertEqual(triggered["status"], "sent")
        self.assertGreaterEqual(len(triggered["deliveries"]), 1)
        self.assertEqual(status_response.json()["daily_report"]["last_run"]["status"], "sent")

    def test_agent_schedule_state_can_be_saved_and_reloaded(self):
        from app.operations_agent.agent_control import (
            get_schedules,
            load_agent_control_state,
            reset_agent_control_state,
            save_agent_control_state,
            update_daily_report_schedule,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["OPERATIONS_AGENT_STATE_PATH"] = os.path.join(tmpdir, "agent_state.json")
            try:
                update_daily_report_schedule(
                    {
                        "enabled": True,
                        "time": "08:45",
                        "channels": ["feishu", "wechat"],
                        "prompt": "生成今日运营日报",
                    }
                )
                save_agent_control_state()
                reset_agent_control_state(persist=False)
                load_agent_control_state()

                schedule = get_schedules()["daily_report"]
                self.assertTrue(schedule["enabled"])
                self.assertEqual(schedule["time"], "08:45")
                self.assertEqual(schedule["channels"], ["feishu", "wechat"])
            finally:
                os.environ.pop("OPERATIONS_AGENT_STATE_PATH", None)

    def test_agent_suggestions_can_be_saved_and_reloaded(self):
        from app.operations_agent.suggestion_store import (
            add_agent_suggestions,
            clear_agent_suggestions,
            list_agent_suggestions,
            load_agent_suggestions,
            save_agent_suggestions,
            update_agent_suggestion_status,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["OPERATIONS_AGENT_SUGGESTIONS_PATH"] = os.path.join(tmpdir, "suggestions.json")
            try:
                created = add_agent_suggestions(
                    actions=[
                        {
                            "title": "上调款式 01 推荐位",
                            "reason": "试戴高且预约转化稳定",
                            "priority": "high",
                            "requires_confirmation": True,
                        }
                    ],
                    source_message="生成推荐位调整建议",
                    answer="建议提升款式 01 曝光。",
                    evidence=[{"label": "试戴", "value": "款式 01 试戴领先", "source": "get_hot_candidates"}],
                )
                update_agent_suggestion_status(created[0]["id"], "accepted")
                save_agent_suggestions()
                clear_agent_suggestions()
                load_agent_suggestions()

                loaded = list_agent_suggestions()

                self.assertEqual(len(loaded), 1)
                self.assertEqual(loaded[0]["title"], "上调款式 01 推荐位")
                self.assertEqual(loaded[0]["status"], "accepted")
                self.assertEqual(loaded[0]["evidence"][0]["source"], "get_hot_candidates")
            finally:
                os.environ.pop("OPERATIONS_AGENT_SUGGESTIONS_PATH", None)
                clear_agent_suggestions()

    def test_agent_schedule_status_exposes_channel_configuration(self):
        from app.operations_agent.agent_control import get_schedules

        status = get_schedules()

        self.assertIn("channels", status)
        self.assertIn("feishu", status["channels"])
        self.assertEqual(status["channels"]["feishu"]["mode"], "webhook")
        self.assertIn(status["channels"]["feishu"]["configured"], [True, False])
        self.assertIn("next_run_at", status["daily_report"])

    def test_external_agent_delivery_marks_feishu_as_mock_when_webhook_missing(self):
        from app.operations_agent.agent_control import handle_external_message

        result = handle_external_message(
            db=None,
            channel="feishu",
            sender="harlan",
            message="生成今日运营日报",
            context={"test": True},
        )

        self.assertEqual(result["delivery_status"], "mock_sent")
        self.assertEqual(result["delivery_channel"], "feishu")
        self.assertTrue(result["reply_text"])

    def test_external_agent_can_sync_previous_action_after_confirmation(self):
        from app.operations_agent.agent_control import handle_external_message, reset_agent_control_state
        from app.operations_agent.suggestion_store import clear_agent_suggestions, list_agent_suggestions

        reset_agent_control_state(persist=False)
        clear_agent_suggestions()
        db = self._create_memory_db()
        self._seed_design_signals(db)

        first = handle_external_message(
            db=db,
            channel="feishu",
            sender="harlan_mobile",
            message="今天哪些预约客户需要优先跟进？",
            context={"test": True},
        )
        second = handle_external_message(
            db=db,
            channel="feishu",
            sender="harlan_mobile",
            message="同步到建议中心",
            context={"test": True},
        )

        self.assertGreaterEqual(len(first["recommended_actions"]), 1)
        self.assertIn("已同步", second["reply_text"])
        self.assertGreaterEqual(len(list_agent_suggestions(status="pending")), 1)

    def test_external_agent_accepts_real_chinese_sync_command(self):
        from app.operations_agent.agent_control import handle_external_message, reset_agent_control_state
        from app.operations_agent.suggestion_store import clear_agent_suggestions, list_agent_suggestions

        reset_agent_control_state(persist=False)
        clear_agent_suggestions()
        db = self._create_memory_db()
        self._seed_design_signals(db)

        first = handle_external_message(
            db=db,
            channel="feishu",
            sender="real_chinese_operator",
            message="今天哪些预约客户需要优先跟进？",
            context={"test": True},
        )
        second = handle_external_message(
            db=db,
            channel="feishu",
            sender="real_chinese_operator",
            message="同步到建议中心",
            context={"test": True},
        )

        self.assertGreaterEqual(len(first["recommended_actions"]), 1)
        self.assertIn("已同步", second["reply_text"])
        self.assertGreaterEqual(len(list_agent_suggestions(status="pending")), 1)

    def test_feishu_event_subscription_challenge_is_supported(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/operations/assistant/webhook/feishu",
            json={"type": "url_verification", "challenge": "feishu-challenge-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["challenge"], "feishu-challenge-token")

    def test_feishu_text_message_event_runs_operations_agent(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/operations/assistant/webhook/feishu",
            json={
                "schema": "2.0",
                "header": {"event_type": "im.message.receive_v1"},
                "event": {
                    "sender": {"sender_id": {"open_id": "harlan_feishu"}},
                    "message": {
                        "message_type": "text",
                        "content": "{\"text\":\"????????\"}",
                    },
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["channel"], "feishu")
        self.assertTrue(response.json()["reply_text"])

    def test_due_daily_report_schedule_runs_once_per_minute(self):
        from app.operations_agent.agent_control import maybe_run_due_daily_report, update_daily_report_schedule

        db = self._create_memory_db()
        update_daily_report_schedule(
            {
                "enabled": True,
                "time": "09:30",
                "channels": ["feishu"],
                "prompt": "生成今日运营日报",
            }
        )

        first = maybe_run_due_daily_report(db=db, now=datetime(2026, 6, 4, 9, 30, 10))
        second = maybe_run_due_daily_report(db=db, now=datetime(2026, 6, 4, 9, 30, 45))

        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_external_agent_can_configure_daily_report_schedule_by_chat(self):
        from app.operations_agent.agent_control import get_schedules, handle_external_message

        db = self._create_memory_db()
        response = handle_external_message(
            db=db,
            channel="feishu",
            sender="harlan_mobile",
            message="开启日报 08:45",
            context={"test": True},
        )
        schedule = get_schedules()["daily_report"]

        self.assertEqual(response["delivery_status"], "mock_sent")
        self.assertIn("08:45", response["reply_text"])
        self.assertTrue(schedule["enabled"])
        self.assertEqual(schedule["time"], "08:45")

    def test_external_agent_can_disable_daily_report_schedule_by_chat(self):
        from app.operations_agent.agent_control import get_schedules, handle_external_message, update_daily_report_schedule

        update_daily_report_schedule(
            {
                "enabled": True,
                "time": "08:45",
                "channels": ["feishu"],
                "prompt": "生成今日运营日报",
            }
        )

        response = handle_external_message(
            db=self._create_memory_db(),
            channel="feishu",
            sender="harlan_mobile",
            message="关闭日报",
            context={"test": True},
        )
        schedule = get_schedules()["daily_report"]

        self.assertEqual(response["delivery_status"], "mock_sent")
        self.assertIn("已关闭", response["reply_text"])
        self.assertFalse(schedule["enabled"])

    def test_external_agent_can_trigger_daily_report_schedule_by_chat(self):
        from app.operations_agent.agent_control import handle_external_message

        db = self._create_memory_db()
        response = handle_external_message(
            db=db,
            channel="feishu",
            sender="harlan_mobile",
            message="立即推送日报",
            context={"test": True},
        )

        self.assertEqual(response["delivery_status"], "mock_sent")
        self.assertIn("已立即推送日报", response["reply_text"])

    def test_external_agent_can_report_daily_schedule_status_by_chat(self):
        from app.operations_agent.agent_control import handle_external_message, update_daily_report_schedule

        update_daily_report_schedule(
            {
                "enabled": True,
                "time": "08:45",
                "channels": ["feishu"],
                "prompt": "生成今日运营日报",
            }
        )

        response = handle_external_message(
            db=self._create_memory_db(),
            channel="feishu",
            sender="harlan_mobile",
            message="日报状态",
            context={"test": True},
        )

        self.assertEqual(response["delivery_status"], "mock_sent")
        self.assertIn("已开启", response["reply_text"])
        self.assertIn("08:45", response["reply_text"])
        self.assertEqual(response["tool_trace"][0]["tool"], "daily_report_schedule_status")

    def test_agent_can_sync_latest_actions_from_chat_when_user_requests_execution(self):
        from app.operations_agent.agent_control import apply_chat_command

        response = apply_chat_command(
            message="同步到建议中心",
            assistant_payload={
                "answer": "建议调整推荐位。",
                "evidence": [
                    {"label": "试戴高预约低", "value": "款式 1 试戴高预约低", "source": "find_high_tryon_low_booking_designs"}
                ],
                "recommended_actions": [
                    {
                        "title": "调整款式 1 推荐位",
                        "reason": "试戴兴趣没有转化成预约",
                        "priority": "high",
                        "requires_confirmation": True,
                    }
                ],
            },
        )

        self.assertEqual(response["status"], "completed")
        self.assertEqual(response["action"], "sync_suggestions")
        self.assertEqual(response["created_count"], 1)


if __name__ == "__main__":
    unittest.main()
