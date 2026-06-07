import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt

from app import models
from app.auth import ALGORITHM, create_access_token
from app.database import SessionLocal
from app.main import app

DEFAULT_SECRET_KEY = "your-secret-key-change-this-in-production"


class AuthContractTest(unittest.TestCase):
    def setUp(self):
        try:
            from app.auth import clear_login_codes

            clear_login_codes()
        except ModuleNotFoundError:
            pass

    def _create_db_user(self, phone: str, user_type: str = "consumer") -> models.User:
        db = SessionLocal()
        try:
            user = models.User(
                phone=phone,
                nickname=f"娴嬭瘯璐﹀彿{phone[-4:]}",
                user_type=user_type,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return models.User(id=user.id, phone=user.phone, nickname=user.nickname, user_type=user.user_type)
        finally:
            db.close()

    def test_consumer_can_login_with_phone_code_and_read_me(self):
        client = TestClient(app)
        phone = "13910000001"

        code_response = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "Harlan", "user_type": "consumer"},
        )

        self.assertEqual(code_response.status_code, 200)
        code = code_response.json()["debug_code"]

        login_response = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": code, "nickname": "Harlan", "user_type": "consumer"},
        )
        token = login_response.json()["access_token"]
        me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["token_type"], "bearer")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["phone"], phone)
        self.assertEqual(me_response.json()["user_type"], "consumer")

    def test_login_normalizes_phone_before_code_and_user_lookup(self):
        client = TestClient(app)
        phone = "13910000020"

        code_response = client.post(
            "/api/auth/request-code",
            json={"phone": f"  {phone}  ", "nickname": "Normalized User", "user_type": "consumer"},
        )

        self.assertEqual(code_response.status_code, 200)
        code = code_response.json()["debug_code"]

        login_response = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": code, "nickname": "Normalized User", "user_type": "consumer"},
        )
        token = login_response.json()["access_token"]
        me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["user"]["phone"], phone)
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["phone"], phone)

    @patch("app.routers.auth.get_settings")
    def test_operator_allowlist_uses_normalized_phone(self, mocked_settings):
        mocked_settings.return_value.DEBUG = True
        mocked_settings.return_value.OPERATOR_PHONES = "13910000021"
        mocked_settings.return_value.SMS_PROVIDER = "debug"
        mocked_settings.return_value.SMS_WEBHOOK_URL = ""
        client = TestClient(app)

        response = client.post(
            "/api/auth/request-code",
            json={"phone": " 13910000021 ", "nickname": "Normalized Operator", "user_type": "admin"},
        )

        self.assertEqual(response.status_code, 200)

    def _login(self, client: TestClient, phone: str, user_type: str = "consumer") -> str:
        code = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": f"娴嬭瘯璐﹀彿{phone[-4:]}", "user_type": user_type},
        ).json()["debug_code"]
        response = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": code, "nickname": f"娴嬭瘯璐﹀彿{phone[-4:]}", "user_type": user_type},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    def test_admin_can_login_with_admin_user_type(self):
        client = TestClient(app)
        phone = "13910000002"

        code = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "杩愯惀璐﹀彿", "user_type": "admin"},
        ).json()["debug_code"]
        login_response = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": code, "nickname": "杩愯惀璐﹀彿", "user_type": "admin"},
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["user"]["user_type"], "admin")

    def test_public_user_create_cannot_assign_operator_role(self):
        client = TestClient(app)

        response = client.post(
            "/api/users/",
            json={"phone": "13910000013", "nickname": "鍏紑鍒涘缓杩愯惀", "user_type": "admin"},
        )

        self.assertEqual(response.status_code, 400)

    def test_public_user_create_normalizes_phone_before_duplicate_check(self):
        client = TestClient(app)
        phone = f"139{uuid4().int % 100000000:08d}"

        created = client.post(
            "/api/users/",
            json={"phone": f" {phone} ", "nickname": "Normalized Public", "user_type": "consumer"},
        )
        duplicate = client.post(
            "/api/users/",
            json={"phone": phone, "nickname": "Duplicate Public", "user_type": "consumer"},
        )

        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["phone"], phone)
        self.assertEqual(duplicate.status_code, 400)

    def test_existing_consumer_can_be_promoted_to_admin_in_local_dev_login(self):
        client = TestClient(app)
        phone = "13910000004"

        consumer_code = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "鍚屾墜鏈哄彿鐢ㄦ埛", "user_type": "consumer"},
        ).json()["debug_code"]
        client.post(
            "/api/auth/login",
            json={"phone": phone, "code": consumer_code, "nickname": "鍚屾墜鏈哄彿鐢ㄦ埛", "user_type": "consumer"},
        )

        admin_code = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "鍚屾墜鏈哄彿杩愯惀", "user_type": "admin"},
        ).json()["debug_code"]
        login_response = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": admin_code, "nickname": "鍚屾墜鏈哄彿杩愯惀", "user_type": "admin"},
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["user"]["user_type"], "admin")

    def test_consumer_token_keeps_consumer_permissions_after_operator_login(self):
        client = TestClient(app)
        phone = f"139{uuid4().int % 100000000:08d}"

        consumer_code = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "Promoted Consumer", "user_type": "consumer"},
        ).json()["debug_code"]
        consumer_login = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": consumer_code, "nickname": "Promoted Consumer", "user_type": "consumer"},
        )
        consumer_token = consumer_login.json()["access_token"]

        admin_code = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "鍗囩骇杩愯惀", "user_type": "admin"},
        ).json()["debug_code"]
        admin_login = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": admin_code, "nickname": "鍗囩骇杩愯惀", "user_type": "admin"},
        )

        response = client.get(
            "/api/operations/assistant/capabilities",
            headers={"Authorization": f"Bearer {consumer_token}"},
        )

        self.assertEqual(admin_login.status_code, 200)
        self.assertEqual(response.status_code, 403)

    def test_same_phone_can_hold_consumer_and_admin_sessions_without_role_bleed(self):
        client = TestClient(app)
        phone = f"139{uuid4().int % 100000000:08d}"

        admin_code = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "Operator", "user_type": "admin"},
        ).json()["debug_code"]
        admin_login = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": admin_code, "nickname": "Operator", "user_type": "admin"},
        )
        self.assertEqual(admin_login.status_code, 200)
        admin_token = admin_login.json()["access_token"]

        consumer_code = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "Consumer", "user_type": "consumer"},
        ).json()["debug_code"]
        consumer_login = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": consumer_code, "nickname": "Consumer", "user_type": "consumer"},
        )
        self.assertEqual(consumer_login.status_code, 200)
        consumer_token = consumer_login.json()["access_token"]

        consumer_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {consumer_token}"})
        admin_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        consumer_ops = client.get(
            "/api/operations/assistant/capabilities",
            headers={"Authorization": f"Bearer {consumer_token}"},
        )
        admin_ops = client.get(
            "/api/operations/assistant/capabilities",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(consumer_login.json()["user"]["id"], admin_login.json()["user"]["id"])
        self.assertEqual(consumer_me.status_code, 200)
        self.assertEqual(consumer_me.json()["user_type"], "consumer")
        self.assertEqual(consumer_me.json()["nickname"], "Consumer")
        self.assertEqual(admin_me.status_code, 200)
        self.assertEqual(admin_me.json()["user_type"], "admin")
        self.assertEqual(admin_me.json()["nickname"], "Operator")
        self.assertEqual(consumer_ops.status_code, 403)
        self.assertEqual(admin_ops.status_code, 200)

    def test_operator_token_cannot_access_consumer_assistant(self):
        client = TestClient(app)
        token = self._login(client, "13910000022", "admin")

        response = client.post(
            "/api/consumer-assistant/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "帮我推荐通勤款"},
        )

        self.assertEqual(response.status_code, 403)

    def test_invalid_code_is_rejected(self):
        client = TestClient(app)
        phone = "13910000003"

        client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "Wrong Code User", "user_type": "consumer"},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": "000000", "nickname": "Wrong Code User", "user_type": "consumer"},
        )

        self.assertEqual(login_response.status_code, 400)

    def test_consumer_code_cannot_be_reused_for_admin_login(self):
        client = TestClient(app)
        phone = "13910000011"

        code = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "瑙掕壊缁戝畾鐢ㄦ埛", "user_type": "consumer"},
        ).json()["debug_code"]
        login_response = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": code, "nickname": "瑙掕壊缁戝畾杩愯惀", "user_type": "admin"},
        )

        self.assertEqual(login_response.status_code, 400)

    def test_admin_code_cannot_be_reused_for_consumer_login(self):
        client = TestClient(app)
        phone = "13910000012"

        code = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "瑙掕壊缁戝畾杩愯惀", "user_type": "admin"},
        ).json()["debug_code"]
        login_response = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": code, "nickname": "瑙掕壊缁戝畾鐢ㄦ埛", "user_type": "consumer"},
        )

        self.assertEqual(login_response.status_code, 400)

    def test_operations_endpoint_requires_token(self):
        client = TestClient(app)

        response = client.get("/api/operations/assistant/capabilities")

        self.assertEqual(response.status_code, 401)

    def test_hand_photo_binary_upload_requires_login(self):
        client = TestClient(app)

        response = client.post(
            "/api/upload/hand-photo",
            files={"file": ("hand.jpg", b"fake image bytes", "image/jpeg")},
        )

        self.assertEqual(response.status_code, 401)

    def test_logged_in_user_can_upload_hand_photo_binary(self):
        client = TestClient(app)
        token = self._login(client, "13910000010", "consumer")

        response = client.post(
            "/api/upload/hand-photo",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("hand.jpg", b"\xff\xd8\xff\xe0" + b"fake image bytes", "image/jpeg")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["url"].startswith("/uploads/hands/hand_"))

    def test_hand_photo_binary_upload_uses_public_asset_base_url_when_configured(self):
        client = TestClient(app)
        token = self._login(client, f"139{uuid4().int % 100000000:08d}", "consumer")

        with patch("app.main.settings.PUBLIC_ASSET_BASE_URL", "https://cdn.example.test/assets/"):
            response = client.post(
                "/api/upload/hand-photo",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("hand.jpg", b"\xff\xd8\xff\xe0" + b"fake image bytes", "image/jpeg")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["url"].startswith("https://cdn.example.test/assets/uploads/hands/hand_"))
        self.assertNotIn("assets//uploads", response.json()["url"])

    def test_hand_photo_binary_upload_rejects_non_image_file(self):
        client = TestClient(app)
        token = self._login(client, "13910000015", "consumer")

        response = client.post(
            "/api/upload/hand-photo",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("notes.txt", b"not an image", "text/plain")},
        )

        self.assertEqual(response.status_code, 400)

    def test_hand_photo_binary_upload_rejects_spoofed_image_mime(self):
        client = TestClient(app)
        token = self._login(client, "13910000017", "consumer")

        response = client.post(
            "/api/upload/hand-photo",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("hand.jpg", b"not really a jpeg", "image/jpeg")},
        )

        self.assertEqual(response.status_code, 400)

    def test_hand_photo_binary_upload_rejects_oversized_file(self):
        client = TestClient(app)
        token = self._login(client, "13910000016", "consumer")

        with patch("app.main.settings.MAX_FILE_SIZE", 4):
            response = client.post(
                "/api/upload/hand-photo",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("hand.jpg", b"too large", "image/jpeg")},
            )

        self.assertEqual(response.status_code, 413)

    def test_invalid_token_is_rejected(self):
        client = TestClient(app)

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        self.assertEqual(response.status_code, 401)

    @patch("app.auth.get_settings")
    def test_production_rejects_default_secret_before_minting_token(self, mocked_settings):
        mocked_settings.return_value = SimpleNamespace(
            DEBUG=False,
            SECRET_KEY=DEFAULT_SECRET_KEY,
            ACCESS_TOKEN_EXPIRE_MINUTES=60,
        )
        user = models.User(id=1, phone="13910000018", user_type="consumer")

        with self.assertRaises(HTTPException) as context:
            create_access_token(user)

        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("SECRET_KEY", context.exception.detail)

    @patch("app.auth.get_settings")
    def test_production_rejects_default_secret_before_accepting_token(self, mocked_settings):
        mocked_settings.return_value = SimpleNamespace(
            DEBUG=False,
            SECRET_KEY=DEFAULT_SECRET_KEY,
            ACCESS_TOKEN_EXPIRE_MINUTES=60,
        )
        client = TestClient(app)
        user = self._create_db_user(f"139{uuid4().int % 100000000:08d}", "admin")
        token = jwt.encode(
            {
                "sub": str(user.id),
                "phone": user.phone,
                "user_type": user.user_type,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            },
            DEFAULT_SECRET_KEY,
            algorithm=ALGORITHM,
        )

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        self.assertEqual(response.status_code, 500)
        self.assertIn("SECRET_KEY", response.json()["detail"])

    def test_consumer_cannot_access_operations_agent(self):
        client = TestClient(app)
        token = self._login(client, "13910000008", "consumer")

        response = client.get(
            "/api/operations/assistant/capabilities",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_operations_agent_capabilities(self):
        client = TestClient(app)
        token = self._login(client, "13910000009", "admin")

        response = client.get(
            "/api/operations/assistant/capabilities",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], "agent-v2")

    @patch("app.routers.auth.get_settings")
    def test_operator_login_requires_configuration_when_not_debug(self, mocked_settings):
        mocked_settings.return_value.DEBUG = False
        mocked_settings.return_value.OPERATOR_PHONES = ""
        mocked_settings.return_value.SMS_PROVIDER = "debug"
        mocked_settings.return_value.SMS_WEBHOOK_URL = ""
        client = TestClient(app)

        response = client.post(
            "/api/auth/request-code",
            json={"phone": "13910000005", "nickname": "Unconfigured Operator", "user_type": "admin"},
        )

        self.assertEqual(response.status_code, 403)

    @patch("app.routers.auth.get_settings")
    def test_operator_phone_allowlist_still_requires_sms_provider(self, mocked_settings):
        mocked_settings.return_value.DEBUG = False
        mocked_settings.return_value.OPERATOR_PHONES = "13910000006"
        mocked_settings.return_value.SMS_PROVIDER = "none"
        mocked_settings.return_value.SMS_WEBHOOK_URL = ""
        client = TestClient(app)
        phone = "13910000006"

        response = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "Allowlisted Operator", "user_type": "admin"},
        )

        self.assertEqual(response.status_code, 503)

    @patch("app.routers.auth.get_settings")
    def test_debug_sms_provider_is_disabled_outside_debug(self, mocked_settings):
        mocked_settings.return_value.DEBUG = False
        mocked_settings.return_value.OPERATOR_PHONES = ""
        mocked_settings.return_value.SMS_PROVIDER = "debug"
        mocked_settings.return_value.SMS_WEBHOOK_URL = ""
        client = TestClient(app)

        response = client.post(
            "/api/auth/request-code",
            json={"phone": "13910000007", "nickname": "鐢熶骇鐢ㄦ埛", "user_type": "consumer"},
        )

        self.assertEqual(response.status_code, 503)

    @patch("app.routers.auth.get_settings")
    def test_failed_sms_send_does_not_leave_usable_login_code(self, mocked_settings):
        mocked_settings.return_value.DEBUG = False
        mocked_settings.return_value.OPERATOR_PHONES = ""
        mocked_settings.return_value.SMS_PROVIDER = "none"
        mocked_settings.return_value.SMS_WEBHOOK_URL = ""
        client = TestClient(app)
        phone = f"139{uuid4().int % 100000000:08d}"

        with patch("app.auth.random.randint", return_value=0):
            response = client.post(
                "/api/auth/request-code",
                json={"phone": phone, "nickname": "鐭俊澶辫触鐢ㄦ埛", "user_type": "consumer"},
            )
        login_response = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": "000000", "nickname": "鐭俊澶辫触鐢ㄦ埛", "user_type": "consumer"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(login_response.status_code, 400)

    @patch("app.routers.auth.get_settings")
    @patch("app.routers.auth.urlopen")
    def test_webhook_sms_provider_sends_code_without_exposing_debug_code(self, mocked_urlopen, mocked_settings):
        mocked_settings.return_value.DEBUG = False
        mocked_settings.return_value.OPERATOR_PHONES = ""
        mocked_settings.return_value.SMS_PROVIDER = "webhook"
        mocked_settings.return_value.SMS_WEBHOOK_URL = "https://sms.example.test/send"
        mocked_urlopen.return_value.__enter__.return_value.status = 204
        client = TestClient(app)
        phone = f"139{uuid4().int % 100000000:08d}"

        with patch("app.auth.random.randint", return_value=123456):
            response = client.post(
                "/api/auth/request-code",
                json={"phone": phone, "nickname": "鐪熷疄鐭俊鐢ㄦ埛", "user_type": "consumer"},
            )

        sent_request = mocked_urlopen.call_args.args[0]

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["debug_code"])
        self.assertEqual(sent_request.full_url, "https://sms.example.test/send")
        self.assertEqual(sent_request.get_method(), "POST")
        self.assertEqual(sent_request.get_header("Content-type"), "application/json")
        self.assertIn(b'"phone":"' + phone.encode("utf-8") + b'"', sent_request.data)
        self.assertIn(b'"code":"123456"', sent_request.data)
        self.assertIn(b'"purpose":"login"', sent_request.data)
        self.assertIn(b'"expires_in_seconds":600', sent_request.data)

    @patch("app.routers.auth.get_settings")
    @patch("app.routers.auth.urlopen")
    def test_webhook_sms_provider_failure_revokes_login_code(self, mocked_urlopen, mocked_settings):
        mocked_settings.return_value.DEBUG = False
        mocked_settings.return_value.OPERATOR_PHONES = ""
        mocked_settings.return_value.SMS_PROVIDER = "webhook"
        mocked_settings.return_value.SMS_WEBHOOK_URL = "https://sms.example.test/send"
        mocked_urlopen.side_effect = OSError("network down")
        client = TestClient(app)
        phone = f"139{uuid4().int % 100000000:08d}"

        with patch("app.auth.random.randint", return_value=0):
            response = client.post(
                "/api/auth/request-code",
                json={"phone": phone, "nickname": "鐭俊寮傚父鐢ㄦ埛", "user_type": "consumer"},
            )
        login_response = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": "000000", "nickname": "鐭俊寮傚父鐢ㄦ埛", "user_type": "consumer"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(login_response.status_code, 400)

    @patch("app.routers.auth.get_settings")
    def test_webhook_sms_provider_requires_webhook_url(self, mocked_settings):
        mocked_settings.return_value.DEBUG = False
        mocked_settings.return_value.OPERATOR_PHONES = ""
        mocked_settings.return_value.SMS_PROVIDER = "webhook"
        mocked_settings.return_value.SMS_WEBHOOK_URL = ""
        client = TestClient(app)

        response = client.post(
            "/api/auth/request-code",
            json={"phone": "13910000019", "nickname": "Missing Sms Webhook", "user_type": "consumer"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("webhook", response.json()["detail"].lower())

    def test_verification_code_is_revoked_after_too_many_wrong_attempts(self):
        client = TestClient(app)
        phone = f"139{uuid4().int % 100000000:08d}"

        code = client.post(
            "/api/auth/request-code",
            json={"phone": phone, "nickname": "Brute Force Guard User", "user_type": "consumer"},
        ).json()["debug_code"]
        for _ in range(5):
            response = client.post(
                "/api/auth/login",
                json={"phone": phone, "code": "000000", "nickname": "Brute Force Guard User", "user_type": "consumer"},
            )
            self.assertEqual(response.status_code, 400)

        login_response = client.post(
            "/api/auth/login",
            json={"phone": phone, "code": code, "nickname": "Brute Force Guard User", "user_type": "consumer"},
        )

        self.assertEqual(login_response.status_code, 400)


if __name__ == "__main__":
    unittest.main()

