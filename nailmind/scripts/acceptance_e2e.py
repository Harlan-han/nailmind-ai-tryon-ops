from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request
from typing import Any


def request_json(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: int = 20,
) -> Any:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
    if not content:
        return None
    return json.loads(content.decode("utf-8"))


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(f"Acceptance failed: {message}")


def phone() -> str:
    return f"139{random.randint(10_000_000, 99_999_999)}"


def login(base: str, user_type: str, nickname: str) -> tuple[str, dict[str, Any]]:
    mobile = phone()
    code = request_json(
        "POST",
        f"{base}/api/auth/request-code",
        {"phone": mobile, "nickname": nickname, "user_type": user_type},
    )["debug_code"]
    payload = request_json(
        "POST",
        f"{base}/api/auth/login",
        {"phone": mobile, "nickname": nickname, "user_type": user_type, "code": code},
    )
    expect(payload["user"]["user_type"] == user_type, f"{user_type} login returned wrong role")
    return payload["access_token"], payload["user"]


def wait_for_try_on_result(base: str, token: str, try_on_id: int, timeout_seconds: int = 180) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    terminal_statuses = {"completed", "failed"}
    record = request_json("GET", f"{base}/api/tryon/{try_on_id}", token=token)

    while record["status"] not in terminal_statuses and time.time() < deadline:
        time.sleep(1)
        record = request_json("GET", f"{base}/api/tryon/{try_on_id}", token=token)

    expect(record["status"] in terminal_statuses, "AI try-on generation did not finish before timeout")
    expect(record["status"] == "completed", f"AI try-on generation failed: {record.get('error_message')}")
    expect(bool(record["result_image_url"]), "completed try-on has no result image")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NailMind local acceptance E2E through real HTTP APIs.")
    parser.add_argument("--backend", default="http://localhost:8004")
    parser.add_argument("--frontend", default="http://localhost:3000")
    parser.add_argument("--ai-service", default="http://localhost:8003")
    args = parser.parse_args()

    backend = args.backend.rstrip("/")
    frontend = args.frontend.rstrip("/")
    ai_service = args.ai_service.rstrip("/")

    print("Checking services...")
    with urllib.request.urlopen(frontend, timeout=8) as response:
        expect(response.status == 200, "frontend is not reachable")
    expect(request_json("GET", f"{backend}/health")["status"] == "healthy", "backend health is not healthy")
    expect(request_json("GET", f"{ai_service}/health")["status"] == "healthy", "AI service health is not healthy")

    print("Logging in consumer...")
    consumer_token, consumer = login(backend, "consumer", "验收用户")
    consumer_phone = consumer["phone"]

    print("Creating a real try-on decision signal...")
    designs = request_json("GET", f"{backend}/api/designs/?limit=1")
    expect(isinstance(designs, list) and len(designs) >= 1, "no active nail design available")
    design = designs[0]

    photo = request_json(
        "POST",
        f"{backend}/api/users/me/hand-photos",
        {"image_url": "/uploads/hands/hand_01.jpg"},
        consumer_token,
    )
    expect(photo["id"] > 0, "hand photo was not created")

    try_on = request_json(
        "POST",
        f"{backend}/api/tryon/",
        {"hand_photo_id": photo["id"], "nail_design_id": design["id"]},
        consumer_token,
    )
    expect(try_on["id"] > 0, "try-on record was not created")

    completed_try_on = wait_for_try_on_result(backend, consumer_token, try_on["id"])

    favorite = request_json(
        "POST",
        f"{backend}/api/favorites/",
        {"nail_design_id": design["id"], "try_on_record_id": try_on["id"]},
        consumer_token,
    )
    expect(favorite["try_on_record_id"] == try_on["id"], "favorite is not linked to try-on")

    candidate = request_json("POST", f"{backend}/api/tryon/{try_on['id']}/candidate", token=consumer_token)
    expect(candidate["is_candidate"] is True, "try-on was not added to candidate list")

    booking = request_json(
        "POST",
        f"{backend}/api/operations/booking-intents",
        {
            "try_on_record_id": try_on["id"],
            "nail_design_id": design["id"],
            "phone": consumer_phone,
            "notes": "acceptance e2e booking",
        },
        consumer_token,
    )
    expect(booking["try_on_record_id"] == try_on["id"], "booking intent is not linked to try-on")

    my_records = request_json("GET", f"{backend}/api/tryon/me/records", token=consumer_token)
    my_candidates = request_json("GET", f"{backend}/api/tryon/me/candidates", token=consumer_token)
    my_preferences = request_json("GET", f"{backend}/api/preferences/me", token=consumer_token)
    expect(any(item["id"] == try_on["id"] for item in my_records), "try-on is missing from user records")
    expect(any(item["id"] == try_on["id"] for item in my_candidates), "try-on is missing from candidate list")
    expect(my_preferences["total_try_ons"] >= 1, "user preference profile did not absorb completed try-on")

    print("Logging in operator and checking business loop...")
    admin_token, admin = login(backend, "admin", "验收运营")

    overview = request_json("GET", f"{backend}/api/operations/overview", token=admin_token)
    workbench = request_json("GET", f"{backend}/api/operations/today-workbench", token=admin_token)
    bookings = request_json("GET", f"{backend}/api/operations/booking-intents?status=pending&limit=100", token=admin_token)
    merchant = request_json("GET", f"{backend}/api/operations/merchant-overview", token=admin_token)
    insights = request_json("GET", f"{backend}/api/operations/ai-insights", token=admin_token)
    trending = request_json("GET", f"{backend}/api/recommendations/trending?limit=8")

    expect(overview["today_try_ons"] >= 1, "operations overview did not count completed try-on")
    expect(overview["today_favorites"] >= 1, "operations overview did not count favorite")
    expect(overview["today_booking_intents"] >= 1, "operations overview did not count booking intent")
    expect(workbench["summary"]["today_try_ons"] >= 1, "today workbench did not count try-on")
    expect(workbench["summary"]["pending_booking_count"] >= 1, "today workbench did not expose pending booking")
    expect(any(item["id"] == booking["id"] for item in bookings), "operator booking queue is missing the booking intent")
    expect(
        any(card["id"] == f"booking_{booking['id']}" for card in workbench["action_cards"]),
        "today workbench is missing booking follow-up action card",
    )
    expect(
        any(consumer_phone in item["detail"] for item in merchant["recent_activity"]),
        "merchant overview recent activity does not include booking phone",
    )
    expect("predictions" in insights and "action_plan" in insights, "AI insights endpoint did not return operations intelligence")
    expect(any(item["id"] == design["id"] for item in trending), "completed try-on design is not present in user-facing trending list")

    try:
        request_json(
            "PATCH",
            f"{backend}/api/operations/booking-intents/{booking['id']}/status?status=completed",
            token=admin_token,
        )
    except urllib.error.HTTPError as exc:
        expect(exc.code == 400, "skipped booking follow-up rejection returned wrong status")
    else:
        raise AssertionError("Acceptance failed: operator can skip booking follow-up status steps")

    updated_booking = request_json(
        "PATCH",
        f"{backend}/api/operations/booking-intents/{booking['id']}/status?status=contacted",
        token=admin_token,
    )
    expect(updated_booking["status"] == "contacted", "operator could not mark booking as contacted")
    contacted_bookings = request_json("GET", f"{backend}/api/operations/booking-intents?status=contacted&limit=100", token=admin_token)
    updated_workbench = request_json("GET", f"{backend}/api/operations/today-workbench", token=admin_token)
    expect(any(item["id"] == booking["id"] for item in contacted_bookings), "contacted booking queue is missing updated booking")
    expect(
        not any(card["id"] == f"booking_{booking['id']}" for card in updated_workbench["action_cards"]),
        "contacted booking still appears as a pending workbench action",
    )

    try:
        request_json("GET", f"{backend}/api/operations/overview", token=consumer_token)
    except urllib.error.HTTPError as exc:
        expect(exc.code == 403, "consumer operations overview rejection returned wrong status")
    else:
        raise AssertionError("Acceptance failed: consumer token can access operator overview")

    print("")
    print("Acceptance E2E passed")
    print(f"  consumer_phone: {consumer_phone}")
    print(f"  admin_phone: {admin['phone']}")
    print(f"  design_id: {design['id']}")
    print(f"  try_on_id: {try_on['id']}")
    print(f"  booking_id: {booking['id']}")
    print(f"  booking_status: {updated_booking['status']}")
    print(
        "  overview: "
        f"try_ons={overview['today_try_ons']}, "
        f"favorites={overview['today_favorites']}, "
        f"bookings={overview['today_booking_intents']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
