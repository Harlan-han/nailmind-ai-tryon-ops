import re
import unittest
from pathlib import Path


class AcceptanceScriptContractTest(unittest.TestCase):
    def test_booking_intent_queries_stay_within_backend_limit_contract(self):
        script = Path(__file__).resolve().parents[2] / "scripts" / "acceptance_e2e.py"
        source = script.read_text(encoding="utf-8")

        limits = [
            int(match.group(1))
            for match in re.finditer(r"booking-intents\?[^\"\n]*limit=(\d+)", source)
        ]

        self.assertGreater(len(limits), 0)
        self.assertTrue(all(limit <= 100 for limit in limits))

    def test_acceptance_waits_for_ai_service_callback_instead_of_manual_webhook(self):
        script = Path(__file__).resolve().parents[2] / "scripts" / "acceptance_e2e.py"
        source = script.read_text(encoding="utf-8")

        self.assertNotIn("/api/tryon/webhook/result", source)
        self.assertIn("wait_for_try_on_result", source)
        self.assertIn('"completed"', source)
        self.assertNotIn("fallback_completed", source)


class LocalStartScriptContractTest(unittest.TestCase):
    def test_start_local_wires_backend_and_ai_ports_into_service_urls(self):
        script = Path(__file__).resolve().parents[2] / "scripts" / "start-local.ps1"
        source = script.read_text(encoding="utf-8")

        self.assertIn('AI_SERVICE_URL', source)
        self.assertIn('BACKEND_WEBHOOK_URL', source)
        self.assertRegex(source, r'localhost:\$AiPort')
        self.assertRegex(source, r'localhost:\$BackendPort/api/tryon/webhook/result')

    def test_start_local_wires_frontend_rewrites_to_custom_backend_and_ai_ports(self):
        script = Path(__file__).resolve().parents[2] / "scripts" / "start-local.ps1"
        source = script.read_text(encoding="utf-8")

        self.assertIn("NEXT_PUBLIC_BACKEND_ORIGIN", source)
        self.assertIn("NEXT_PUBLIC_API_BASE_URL", source)
        self.assertIn("NEXT_PUBLIC_AI_SERVICE_ORIGIN", source)
        self.assertRegex(source, r'localhost:\$BackendPort/api')
        self.assertRegex(source, r'localhost:\$AiPort')

    def test_start_local_forwards_tryon_provider_to_ai_service(self):
        script = Path(__file__).resolve().parents[2] / "scripts" / "start-local.ps1"
        source = script.read_text(encoding="utf-8")

        self.assertIn("NAILMIND_TRYON_PROVIDER", source)


if __name__ == "__main__":
    unittest.main()
