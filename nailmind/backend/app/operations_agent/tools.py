"""Read-only operations tools exposed to the LLM agent."""
from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.routers import operations
from app.operations_agent import design_signals, reports


TOOL_SPECS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_overview",
            "description": "Get today's operations overview and trending styles.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trends",
            "description": "Get try-on, user, style, and color trends for a time window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 30}
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hot_candidates",
            "description": "Get rising nail design candidates that may deserve promotion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5}
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cold_designs",
            "description": "Get active designs with weak conversion or low performance.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_funnel",
            "description": "Get conversion funnel metrics for a time window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 30}
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ai_insights",
            "description": "Get the existing rule-based AI insights report.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_report",
            "description": "Generate today's operations report from current data.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weekly_report",
            "description": "Generate a weekly operations report from try-on, favorite, booking, style, and design signals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 7}
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendation_slot_plan",
            "description": "Generate a read-only recommendation slot plan that separates promote, demote, and observe actions for human confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5}
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_action_plan",
            "description": "Get a rule-based operations action plan.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_suggestions",
            "description": "Get generated operation suggestions waiting for human review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "default": "pending"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_booking_followups",
            "description": "Get booking intent customers that need merchant follow-up, including user, phone, design, try-on result image, and current follow-up status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "default": "pending"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_design_performance",
            "description": "Analyze one nail design's view, try-on, favorite, booking, and converted try-on image signals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "design_id": {"type": "integer", "minimum": 1},
                },
                "required": ["design_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_hot_design",
            "description": "Explain why a nail design is hot or only a potential candidate based on conversion evidence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "design_id": {"type": "integer", "minimum": 1},
                },
                "required": ["design_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_high_tryon_low_booking_designs",
            "description": "Find designs with high try-on interest but weak booking conversion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_high_favorite_low_booking_designs",
            "description": "Find designs users save often but rarely book.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_converted_tryon_images",
            "description": "Find completed AI try-on result images that led to booking intent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
                },
                "additionalProperties": False,
            },
        },
    },
]


def get_tool_definitions() -> List[Dict[str, Any]]:
    return TOOL_SPECS


def _safe_int(value: Any, default: int, min_value: int = 1, max_value: int = 90) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(parsed, max_value))


class OperationsToolRegistry:
    """Executes a small whitelist of read-only operations tools."""

    def execute(self, name: str, arguments: Dict[str, Any] | None, db: Session) -> Dict[str, Any]:
        args = arguments or {}

        if name == "get_overview":
            return {"tool": name, "data": operations.get_overview(db=db).model_dump()}
        if name == "get_trends":
            return {"tool": name, "data": operations.get_trends(days=_safe_int(args.get("days"), 30), db=db)}
        if name == "get_hot_candidates":
            return {
                "tool": name,
                "data": {
                    "items": operations.get_hot_candidates(
                        limit=_safe_int(args.get("limit"), 5, max_value=20),
                        db=db,
                    )
                },
            }
        if name == "get_cold_designs":
            return {"tool": name, "data": {"items": operations.get_cold_designs(db=db)[:10]}}
        if name == "get_funnel":
            return {"tool": name, "data": operations.get_funnel(days=_safe_int(args.get("days"), 30), db=db)}
        if name == "get_ai_insights":
            return {"tool": name, "data": operations.get_ai_insights(db=db)}
        if name == "get_daily_report":
            report = operations.get_daily_report(db=db)
            return {"tool": name, "data": report.model_dump() if hasattr(report, "model_dump") else report}
        if name == "get_weekly_report":
            return {
                "tool": name,
                "data": reports.build_weekly_report(
                    db=db,
                    days=_safe_int(args.get("days"), 7),
                ),
            }
        if name == "get_recommendation_slot_plan":
            return {
                "tool": name,
                "data": reports.build_recommendation_slot_plan(
                    db=db,
                    limit=_safe_int(args.get("limit"), 5, max_value=20),
                ),
            }
        if name == "get_action_plan":
            return {"tool": name, "data": operations.get_action_plan(db=db)}
        if name == "get_suggestions":
            return {
                "tool": name,
                "data": {
                    "items": operations.get_suggestions(
                        status=args.get("status") or None,
                        limit=_safe_int(args.get("limit"), 5, max_value=20),
                        db=db,
                    )
                },
            }
        if name == "get_booking_followups":
            return {
                "tool": name,
                "data": {
                    "items": operations.list_booking_intents(
                        status=args.get("status") or None,
                        limit=_safe_int(args.get("limit"), 10, max_value=20),
                        db=db,
                    )
                },
            }
        if name == "analyze_design_performance":
            return {
                "tool": name,
                "data": design_signals.analyze_design_performance(
                    db=db,
                    design_id=_safe_int(args.get("design_id"), 1),
                ),
            }
        if name == "explain_hot_design":
            return {
                "tool": name,
                "data": design_signals.explain_hot_design(
                    db=db,
                    design_id=_safe_int(args.get("design_id"), 1),
                ),
            }
        if name == "find_high_tryon_low_booking_designs":
            return {
                "tool": name,
                "data": {
                    "items": design_signals.find_high_tryon_low_booking_designs(
                        db=db,
                        limit=_safe_int(args.get("limit"), 10, max_value=20),
                    )
                },
            }
        if name == "find_high_favorite_low_booking_designs":
            return {
                "tool": name,
                "data": {
                    "items": design_signals.find_high_favorite_low_booking_designs(
                        db=db,
                        limit=_safe_int(args.get("limit"), 10, max_value=20),
                    )
                },
            }
        if name == "find_converted_tryon_images":
            return {
                "tool": name,
                "data": {
                    "items": design_signals.find_converted_tryon_images(
                        db=db,
                        limit=_safe_int(args.get("limit"), 10, max_value=20),
                    )
                },
            }

        raise ValueError(f"Unsupported operations tool: {name}")
