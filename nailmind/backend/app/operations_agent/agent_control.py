"""Control layer for external Agent channels and scheduled operations tasks."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.operations_agent.llm_client import DeepSeekClient
from app.operations_agent.runner import OperationsAgentRunner
from app.operations_agent.suggestion_store import add_agent_suggestions


DEFAULT_DAILY_REPORT_PROMPT = "生成今日运营日报"
SUPPORTED_CHANNELS = ("feishu", "wechat", "qq")

_daily_report_schedule: Dict[str, Any] = {
    "enabled": False,
    "time": "09:30",
    "channels": ["feishu"],
    "prompt": DEFAULT_DAILY_REPORT_PROMPT,
    "last_run": None,
    "last_due_key": None,
}
_external_deliveries: List[Dict[str, Any]] = []
_external_last_payloads: Dict[str, Dict[str, Any]] = {}


def _state_path() -> Path:
    configured = os.getenv("OPERATIONS_AGENT_STATE_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "data" / "operations_agent_state.json"


def load_agent_control_state() -> None:
    path = _state_path()
    if not path.exists():
        return
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    schedule = state.get("daily_report")
    if isinstance(schedule, dict):
        _daily_report_schedule.update(
            {
                "enabled": bool(schedule.get("enabled", _daily_report_schedule["enabled"])),
                "time": _normalize_time(str(schedule.get("time") or _daily_report_schedule["time"])),
                "channels": [
                    _normalize_channel(str(channel))
                    for channel in schedule.get("channels", _daily_report_schedule["channels"])
                    if str(channel).strip()
                ] or ["feishu"],
                "prompt": str(schedule.get("prompt") or DEFAULT_DAILY_REPORT_PROMPT),
                "last_run": schedule.get("last_run"),
                "last_due_key": schedule.get("last_due_key"),
            }
        )

    deliveries = state.get("deliveries")
    if isinstance(deliveries, list):
        _external_deliveries.clear()
        _external_deliveries.extend(item for item in deliveries[:20] if isinstance(item, dict))


def save_agent_control_state() -> None:
    path = _state_path()
    state = {
        "daily_report": dict(_daily_report_schedule),
        "deliveries": list(_external_deliveries[:20]),
        "updated_at": datetime.now().isoformat(),
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except OSError:
        return


def reset_agent_control_state(persist: bool = False) -> None:
    _daily_report_schedule.update(
        {
            "enabled": False,
            "time": "09:30",
            "channels": ["feishu"],
            "prompt": DEFAULT_DAILY_REPORT_PROMPT,
            "last_run": None,
            "last_due_key": None,
        }
    )
    _external_deliveries.clear()
    _external_last_payloads.clear()
    if persist:
        save_agent_control_state()


def get_channel_statuses() -> Dict[str, Dict[str, Any]]:
    settings = get_settings()
    feishu_webhook = settings.FEISHU_BOT_WEBHOOK_URL or os.getenv("FEISHU_BOT_WEBHOOK_URL", "")
    return {
        "feishu": {
            "label": "飞书群机器人",
            "mode": "webhook",
            "status": "connected" if feishu_webhook else "simulated",
            "configured": bool(feishu_webhook),
            "inbound": "webhook",
            "outbound": "bot_webhook",
            "required_env": ["FEISHU_BOT_WEBHOOK_URL"],
            "description": "配置 FEISHU_BOT_WEBHOOK_URL 后可推送到真实飞书群。",
            "setup_steps": [
                "在飞书开放平台创建机器人或在群内添加自定义机器人。",
                "把事件订阅地址配置为 /api/operations/assistant/webhook/feishu。",
                "如需主动推送日报，在后端启动环境配置 FEISHU_BOT_WEBHOOK_URL。",
            ],
            "message_examples": [
                "今天有什么异常？",
                "生成今日运营日报",
                "开启日报 09:30",
                "立即推送日报",
                "同步到建议中心",
            ],
        },
        "wechat": {
            "label": "微信",
            "mode": "mock",
            "status": "simulated",
            "configured": False,
            "inbound": "generic_webhook",
            "outbound": "mock",
            "required_env": [],
            "description": "当前为统一 Webhook 模拟通道，后续可接企业微信/公众号回调。",
            "setup_steps": [
                "先用通用 Webhook 适配企业微信/公众号消息。",
                "把文本消息转发到 /api/operations/assistant/webhook。",
                "生产环境配置 OPERATIONS_AGENT_EXTERNAL_TOKEN 做回调校验。",
            ],
            "message_examples": [
                "生成今日运营日报",
                "哪些试戴图带来了预约？",
                "关闭日报",
            ],
        },
        "qq": {
            "label": "QQ",
            "mode": "mock",
            "status": "simulated",
            "configured": False,
            "inbound": "generic_webhook",
            "outbound": "mock",
            "required_env": [],
            "description": "当前为统一 Webhook 模拟通道，后续可接 QQ Bot 回调。",
            "setup_steps": [
                "用 QQ Bot 网关把群聊文本转发到通用 Webhook。",
                "请求体包含 channel=qq、sender、text 即可复用同一 Agent。",
                "写操作仍只生成待确认动作卡，不自动改推荐位。",
            ],
            "message_examples": [
                "今天最该推哪 3 个款？",
                "日报状态",
                "同步到建议中心",
            ],
        },
    }


def format_external_reply(answer: str, actions: List[Dict[str, Any]], evidence: List[Dict[str, Any]]) -> str:
    lines = [answer.strip() or "已生成运营分析。"]
    if evidence:
        lines.append("")
        lines.append("使用的数据：")
        for item in evidence[:4]:
            lines.append(f"- {item.get('label')}: {item.get('value')}（{item.get('source')}）")
    if actions:
        lines.append("")
        lines.append("建议动作：")
        for action in actions[:4]:
            lines.append(f"- {action.get('title')}（{action.get('priority', 'medium')}）")
        lines.append("")
        lines.append("回复“同步到建议中心”可生成待确认动作卡。")
    return "\n".join(lines)


def handle_external_message(
    db: Session | None,
    channel: str,
    sender: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_channel = _normalize_channel(channel)
    session_key = _external_session_key(normalized_channel, sender)
    schedule_command = _try_handle_schedule_command(db, normalized_channel, sender, message)
    if schedule_command:
        return schedule_command

    if _is_sync_command(message):
        previous_payload = _external_last_payloads.get(session_key)
        if previous_payload:
            command_result = apply_chat_command(message, previous_payload)
            reply_text = command_result.get("message") or "已处理端外确认指令。"
            delivery_status = deliver_external_reply(normalized_channel, reply_text)
            delivery = {
                "id": f"external_{len(_external_deliveries) + 1}",
                "channel": normalized_channel,
                "sender": sender,
                "message": message,
                "reply_text": reply_text,
                "response": previous_payload,
                "delivery_status": delivery_status["status"],
                "delivery_detail": delivery_status.get("detail"),
                "created_at": datetime.now().isoformat(),
                "command_result": command_result,
            }
            _external_deliveries.insert(0, delivery)
            save_agent_control_state()
            return {
                "channel": normalized_channel,
                "delivery_channel": normalized_channel,
                "delivery_status": delivery_status["status"],
                "delivery_detail": delivery_status.get("detail"),
                "sender": sender,
                "reply_text": reply_text,
                "evidence": previous_payload.get("evidence") or [],
                "recommended_actions": previous_payload.get("recommended_actions") or [],
                "tool_trace": previous_payload.get("tool_trace") or [],
                "created_at": delivery["created_at"],
            }

    runner = OperationsAgentRunner()
    response = runner.chat(
        message=message,
        db=db,
        context={**(context or {}), "channel": normalized_channel, "sender": sender},
    )
    payload = response.model_dump()
    reply_text = format_external_reply(
        payload.get("answer") or "",
        payload.get("recommended_actions") or [],
        payload.get("evidence") or [],
    )
    delivery_status = deliver_external_reply(normalized_channel, reply_text)
    delivery = {
        "id": f"external_{len(_external_deliveries) + 1}",
        "channel": normalized_channel,
        "sender": sender,
        "message": message,
        "reply_text": reply_text,
        "response": payload,
        "delivery_status": delivery_status["status"],
        "delivery_detail": delivery_status.get("detail"),
        "created_at": datetime.now().isoformat(),
    }
    _external_deliveries.insert(0, delivery)
    _external_last_payloads[session_key] = payload
    save_agent_control_state()
    return {
        "channel": normalized_channel,
        "delivery_channel": normalized_channel,
        "delivery_status": delivery_status["status"],
        "delivery_detail": delivery_status.get("detail"),
        "sender": sender,
        "reply_text": reply_text,
        "evidence": payload.get("evidence") or [],
        "recommended_actions": payload.get("recommended_actions") or [],
        "tool_trace": payload.get("tool_trace") or [],
        "created_at": delivery["created_at"],
    }


def _try_handle_schedule_command(
    db: Session | None,
    channel: str,
    sender: str,
    message: str,
) -> Optional[Dict[str, Any]]:
    normalized = message.strip()
    if not any(keyword in normalized for keyword in ["日报", "日報"]):
        return None

    if any(keyword in normalized for keyword in ["状态", "配置", "订阅情况", "开了吗", "是否开启"]):
        schedule = get_schedules()["daily_report"]
        enabled_text = "已开启" if schedule.get("enabled") else "未开启"
        channels = "、".join(schedule.get("channels") or ["feishu"])
        next_run = schedule.get("next_run_at") or "暂无"
        return _command_reply(
            channel=channel,
            sender=sender,
            source_message=message,
            reply_text=(
                f"自动运营日报{enabled_text}。推送时间：{schedule.get('time', '09:30')}；"
                f"通道：{channels}；下次计划推送：{next_run}。"
            ),
            command_result={
                "status": "completed",
                "action": "daily_report_schedule_status",
                "schedule": schedule,
            },
        )

    time_match = re.search(r"([01]?\d|2[0-3])[:：点时]([0-5]\d)?", normalized)
    if any(keyword in normalized for keyword in ["开启", "打开", "启用", "设置", "订阅"]):
        time_value = _normalize_time(
            f"{time_match.group(1)}:{time_match.group(2) or '00'}" if time_match else _daily_report_schedule["time"]
        )
        schedule = update_daily_report_schedule(
            {
                "enabled": True,
                "time": time_value,
                "channels": [channel],
                "prompt": DEFAULT_DAILY_REPORT_PROMPT,
            }
        )
        return _command_reply(
            channel=channel,
            sender=sender,
            source_message=message,
            reply_text=f"已开启自动运营日报，每天 {schedule['time']} 推送到{get_channel_statuses()[channel]['label']}。",
            command_result={"status": "completed", "action": "enable_daily_report", "schedule": schedule},
        )

    if any(keyword in normalized for keyword in ["关闭", "停用", "取消", "停止"]):
        schedule = update_daily_report_schedule({**_daily_report_schedule, "enabled": False})
        return _command_reply(
            channel=channel,
            sender=sender,
            source_message=message,
            reply_text=f"已关闭自动运营日报。你仍可随时发送“立即推送日报”手动触发。",
            command_result={"status": "completed", "action": "disable_daily_report", "schedule": schedule},
        )

    if any(keyword in normalized for keyword in ["立即", "现在", "马上", "推送", "发送"]):
        result = run_daily_report_schedule(db=db)
        targets = "、".join(item.get("channel", channel) for item in result.get("deliveries", [])) or channel
        return _command_reply(
            channel=channel,
            sender=sender,
            source_message=message,
            reply_text=f"已立即推送日报到 {targets}，状态：{result['status']}。",
            command_result={"status": "completed", "action": "run_daily_report", "result": result},
        )

    return None


def _command_reply(
    channel: str,
    sender: str,
    source_message: str,
    reply_text: str,
    command_result: Dict[str, Any],
) -> Dict[str, Any]:
    delivery_status = deliver_external_reply(channel, reply_text)
    delivery = {
        "id": f"external_{len(_external_deliveries) + 1}",
        "channel": channel,
        "sender": sender,
        "message": source_message,
        "reply_text": reply_text,
        "response": {},
        "delivery_status": delivery_status["status"],
        "delivery_detail": delivery_status.get("detail"),
        "created_at": datetime.now().isoformat(),
        "command_result": command_result,
    }
    _external_deliveries.insert(0, delivery)
    save_agent_control_state()
    return {
        "channel": channel,
        "delivery_channel": channel,
        "delivery_status": delivery_status["status"],
        "delivery_detail": delivery_status.get("detail"),
        "sender": sender,
        "reply_text": reply_text,
        "evidence": [],
        "recommended_actions": [],
        "tool_trace": [
            {
                "tool": command_result.get("action", "agent_command"),
                "status": command_result.get("status", "completed"),
                "summary": "external command",
            }
        ],
        "created_at": delivery["created_at"],
    }


def deliver_external_reply(channel: str, reply_text: str) -> Dict[str, Any]:
    channel_statuses = get_channel_statuses()
    status = channel_statuses.get(channel)
    if not status:
        return {"status": "failed", "detail": f"Unsupported channel: {channel}"}

    if channel == "feishu" and status["configured"]:
        webhook_url = get_settings().FEISHU_BOT_WEBHOOK_URL or os.getenv("FEISHU_BOT_WEBHOOK_URL", "")
        try:
            with httpx.Client(trust_env=False, timeout=15.0) as client:
                response = client.post(
                    webhook_url,
                    json={"msg_type": "text", "content": {"text": reply_text}},
                )
                response.raise_for_status()
            return {"status": "sent", "detail": "Feishu webhook delivered"}
        except Exception as exc:
            return {"status": "failed", "detail": str(exc)[:300]}

    return {
        "status": "mock_sent",
        "detail": f"{status['label']} 未配置真实机器人，已记录为端外模拟消息。",
    }


def apply_chat_command(message: str, assistant_payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = message.strip()
    if not _is_sync_command(normalized):
        return {
            "status": "ignored",
            "action": "none",
            "message": "当前指令不属于安全执行动作。",
        }

    actions = assistant_payload.get("recommended_actions") or []
    if not actions:
        return {
            "status": "skipped",
            "action": "sync_suggestions",
            "created_count": 0,
            "message": "当前回答没有可同步的行动卡。",
        }

    created = add_agent_suggestions(
        actions=actions,
        source_message=message,
        answer=assistant_payload.get("answer"),
        evidence=assistant_payload.get("evidence") or [],
    )
    return {
        "status": "completed",
        "action": "sync_suggestions",
        "created_count": len(created),
        "items": created,
        "message": f"已同步 {len(created)} 条建议到建议中心，等待人工确认。",
    }


def get_schedules() -> Dict[str, Any]:
    schedule = dict(_daily_report_schedule)
    schedule["next_run_at"] = calculate_next_run_at(schedule).isoformat() if schedule.get("enabled") else None
    schedule["manual_trigger_path"] = "/api/operations/assistant/schedules/daily-report/run"
    schedule["configure_path"] = "/api/operations/assistant/schedules/daily-report"
    schedule["commands"] = ["开启日报 09:30", "关闭日报", "日报状态", "立即推送日报"]
    schedule.pop("last_due_key", None)
    return {
        "daily_report": schedule,
        "deliveries": list(_external_deliveries[:20]),
        "available_channels": list(SUPPORTED_CHANNELS),
        "channels": get_channel_statuses(),
    }


def get_agent_runtime_status() -> Dict[str, Any]:
    schedules = get_schedules()
    llm_client = DeepSeekClient()
    return {
        "runtime": {
            "entrypoint": "chat",
            "version": "agent-v2",
            "llm_provider": "deepseek",
            "llm_configured": llm_client.available,
            "model": llm_client.model,
            "tool_calling": True,
            "scheduler": "in_process",
        },
        "openclaw_patterns": [
            "multi_channel_gateway",
            "tool_workspace",
            "scheduled_trigger",
            "safe_action_approval",
        ],
        "channels": schedules["channels"],
        "gateway": {
            "primary_inbox": "feishu",
            "webhook_paths": [
                "/api/operations/assistant/webhook/feishu",
                "/api/operations/assistant/webhook",
            ],
            "connectors": schedules["channels"],
            "quick_setup": [
                {
                    "channel": "feishu",
                    "title": "飞书群机器人",
                    "webhook_url": "/api/operations/assistant/webhook/feishu",
                    "outbound_env": "FEISHU_BOT_WEBHOOK_URL",
                    "recommended_for": "产品演示和真实手机端运营通知",
                },
                {
                    "channel": "wechat",
                    "title": "微信/企微适配器",
                    "webhook_url": "/api/operations/assistant/webhook",
                    "outbound_env": None,
                    "recommended_for": "后续接企业微信、公众号或个人微信网关",
                },
                {
                    "channel": "qq",
                    "title": "QQ Bot 适配器",
                    "webhook_url": "/api/operations/assistant/webhook",
                    "outbound_env": None,
                    "recommended_for": "社群运营消息查询和日报模拟",
                },
            ],
            "security": [
                "token_optional_in_debug",
                "token_required_in_production",
                "manual_confirmation_required",
            ],
        },
        "scheduled_tasks": {
            "daily_report": schedules["daily_report"],
        },
        "recent_deliveries": schedules["deliveries"],
        "suggested_commands": [
            "今天有什么异常？",
            "生成今日运营日报",
            "开启日报 09:30",
            "立即推送日报",
            "同步到建议中心",
        ],
        "automation_playbook": {
            "commands": ["开启日报 09:30", "日报状态", "立即推送日报", "关闭日报"],
            "safe_actions": [
                "生成日报和周报",
                "把 Agent 建议同步到建议中心",
                "配置日报定时推送",
            ],
            "blocked_actions": [
                "不自动修改推荐位",
                "不自动群发营销消息",
                "不跳过人工确认执行运营动作",
            ],
        },
        "safety": {
            "execution_policy": [
                "read_only_data_tools",
                "safe_action_approval",
                "manual_confirmation_required",
            ],
            "write_actions": [
                "sync_suggestions",
                "configure_daily_report",
                "trigger_daily_report",
            ],
        },
    }


def update_daily_report_schedule(payload: Dict[str, Any]) -> Dict[str, Any]:
    enabled = bool(payload.get("enabled", _daily_report_schedule["enabled"]))
    time_value = _normalize_time(str(payload.get("time") or _daily_report_schedule["time"]))
    raw_channels = payload.get("channels") or _daily_report_schedule["channels"]
    channels = [_normalize_channel(str(channel)) for channel in raw_channels if str(channel).strip()]
    prompt = str(payload.get("prompt") or _daily_report_schedule["prompt"]).strip() or DEFAULT_DAILY_REPORT_PROMPT

    _daily_report_schedule.update(
        {
            "enabled": enabled,
            "time": time_value,
            "channels": channels or ["feishu"],
            "prompt": prompt,
        }
    )
    save_agent_control_state()
    return get_schedules()["daily_report"]


def run_daily_report_schedule(db: Session | None) -> Dict[str, Any]:
    channels = _daily_report_schedule.get("channels") or ["feishu"]
    prompt = _daily_report_schedule.get("prompt") or DEFAULT_DAILY_REPORT_PROMPT
    deliveries = [
        handle_external_message(
            db=db,
            channel=channel,
            sender="scheduled_daily_report",
            message=prompt,
            context={"trigger": "schedule", "task": "daily-report"},
        )
        for channel in channels
    ]
    has_failure = any(item.get("delivery_status") == "failed" for item in deliveries)
    result = {
        "task": "daily-report",
        "status": "partial_failed" if has_failure else "sent",
        "run_at": datetime.now().isoformat(),
        "deliveries": deliveries,
    }
    _daily_report_schedule["last_run"] = result
    save_agent_control_state()
    return result


def calculate_next_run_at(schedule: Dict[str, Any], now: Optional[datetime] = None) -> datetime:
    current = now or datetime.now()
    hour, minute = _parse_time(schedule.get("time") or "09:30")
    candidate = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= current:
        candidate += timedelta(days=1)
    return candidate


def maybe_run_due_daily_report(db: Session | None = None, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    if not _daily_report_schedule.get("enabled"):
        return None

    current = now or datetime.now()
    hour, minute = _parse_time(_daily_report_schedule.get("time") or "09:30")
    if current.hour != hour or current.minute != minute:
        return None

    due_key = current.strftime("%Y-%m-%d %H:%M")
    if _daily_report_schedule.get("last_due_key") == due_key:
        return None

    _daily_report_schedule["last_due_key"] = due_key
    if db is not None:
        return run_daily_report_schedule(db)

    with SessionLocal() as session:
        return run_daily_report_schedule(session)


def _normalize_channel(channel: str) -> str:
    normalized = channel.strip().lower()
    if normalized not in SUPPORTED_CHANNELS:
        return "feishu"
    return normalized


def _external_session_key(channel: str, sender: str) -> str:
    return f"{channel}:{sender.strip() or 'external_operator'}"


def _is_sync_command(message: str) -> bool:
    normalized = message.strip()
    return any(keyword in normalized for keyword in ["同步", "建议中心", "生成建议", "保存建议"])


def _normalize_time(value: str) -> str:
    hour, minute = _parse_time(value)
    return f"{hour:02d}:{minute:02d}"


def _parse_time(value: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = value.split(":", 1)
        hour = max(0, min(int(hour_text), 23))
        minute = max(0, min(int(minute_text), 59))
        return hour, minute
    except (ValueError, AttributeError):
        return 9, 30


load_agent_control_state()
