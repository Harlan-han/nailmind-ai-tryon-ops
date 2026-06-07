"""Local store for Agent-generated suggestions.

The store uses a JSON file for the local demo so Agent action cards survive
service restarts without requiring a database schema migration.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from itertools import count
from pathlib import Path
from typing import Any, Dict, List, Optional


_agent_suggestions: List[Dict[str, Any]] = []
_id_counter = count(1)


def _state_path() -> Path:
    configured = os.getenv("OPERATIONS_AGENT_SUGGESTIONS_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "data" / "operations_agent_suggestions.json"


def load_agent_suggestions() -> None:
    path = _state_path()
    if not path.exists():
        return

    try:
        raw_state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    suggestions = raw_state.get("suggestions") if isinstance(raw_state, dict) else raw_state
    if not isinstance(suggestions, list):
        return

    _agent_suggestions.clear()
    _agent_suggestions.extend(item for item in suggestions if isinstance(item, dict))
    _reset_id_counter()


def save_agent_suggestions() -> None:
    path = _state_path()
    state = {
        "suggestions": _agent_suggestions,
        "updated_at": datetime.now().isoformat(),
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except OSError:
        return


def add_agent_suggestions(
    actions: List[Dict[str, Any]],
    source_message: Optional[str] = None,
    answer: Optional[str] = None,
    evidence: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    created_items: List[Dict[str, Any]] = []
    now = datetime.now().isoformat()

    for action in actions:
        item = {
            "id": f"agent_{next(_id_counter)}",
            "type": "agent",
            "priority": action.get("priority") or "medium",
            "title": action.get("title") or "运营 Agent 建议",
            "description": action.get("reason") or answer or "由运营 Agent 根据当前数据生成。",
            "target": action.get("title") or "运营动作",
            "reason": action.get("reason") or "",
            "expected_impact": "需人工确认后执行",
            "risk": action.get("risk"),
            "requires_confirmation": action.get("requires_confirmation", True),
            "status": "pending",
            "created_at": now,
            "source": "operations_agent",
            "source_message": source_message,
            "answer": answer,
            "evidence": evidence or [],
        }
        _agent_suggestions.insert(0, item)
        created_items.append(item)

    if created_items:
        save_agent_suggestions()

    return created_items


def list_agent_suggestions(status: Optional[str] = None) -> List[Dict[str, Any]]:
    if status:
        return [item for item in _agent_suggestions if item["status"] == status]
    return list(_agent_suggestions)


def update_agent_suggestion_status(suggestion_id: str, status: str) -> Optional[Dict[str, Any]]:
    for item in _agent_suggestions:
        if item["id"] == suggestion_id:
            item["status"] = status
            save_agent_suggestions()
            return item
    return None


def clear_agent_suggestions(persist: bool = False) -> None:
    _agent_suggestions.clear()
    _reset_id_counter()
    if persist:
        save_agent_suggestions()


def _reset_id_counter() -> None:
    global _id_counter
    max_id = 0
    for item in _agent_suggestions:
        raw_id = str(item.get("id", ""))
        if raw_id.startswith("agent_"):
            try:
                max_id = max(max_id, int(raw_id.split("_", 1)[1]))
            except ValueError:
                continue
    _id_counter = count(max_id + 1)


load_agent_suggestions()
