"""Consumer-facing nail try-on assistant routes."""
from __future__ import annotations

from collections import Counter, deque
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import require_consumer, require_operator
from app.database import get_db
from app.operations_agent.llm_client import DeepSeekClient
from app.services.design_visual_tags import design_to_effective_tags, filter_servable_designs

router = APIRouter()

PERSONA_NAME = "小甲灵"
_RECENT_EVENTS: deque[dict[str, Any]] = deque(maxlen=80)

QUERY_INTENT_TERMS = {
    "短甲": ["短甲", "日常", "通勤", "裸感", "极简", "纯色"],
    "自然": ["裸感", "极简", "纯色", "裸色", "米色", "日常"],
    "低调": ["裸感", "极简", "纯色", "通勤", "日常"],
    "不夸张": ["裸感", "极简", "纯色", "通勤", "日常"],
    "通勤": ["通勤", "日常", "短甲", "裸感", "极简", "高级感"],
    "上班": ["通勤", "日常", "短甲", "裸感", "极简"],
    "显白": ["显白", "裸色", "米色", "粉色", "红色", "法式", "闪粉"],
    "肤色": ["裸色", "米色", "粉色", "裸感"],
    "黑黄皮": ["显白", "裸色", "米色", "红色", "法式"],
    "约会": ["约会", "甜美", "粉色", "爱心", "蝴蝶结", "花朵"],
    "甜": ["甜美", "粉色", "爱心", "蝴蝶结", "花朵"],
    "高级": ["高级感", "裸感", "法式", "猫眼", "金属感", "镜面"],
    "酷": ["甜酷", "黑色系", "星星", "金属感", "猫眼"],
    "派对": ["派对", "甜酷", "黑色系", "金属感", "星星"],
    "婚礼": ["婚礼", "法式", "水钻", "珍珠", "裸感"],
    "节日": ["节日", "红色", "爱心", "金色", "多巴胺"],
    "猫眼": ["猫眼", "金属感", "闪粉"],
    "法式": ["法式", "裸感", "高级感"],
    "爱心": ["爱心", "甜美", "粉色", "约会"],
    "黑色": ["黑色", "黑色系", "甜酷", "派对"],
}


def _demo_events() -> list[dict[str, Any]]:
    now = datetime.now().isoformat()
    return [
        {
            "user_id": "demo_1",
            "user_name": "小鹿",
            "message": "我想要通勤显白一点，不要太夸张",
            "recommended_designs": ["显白法式款", "裸感细闪款"],
            "top_tags": ["法式", "裸感", "通勤"],
            "created_at": now,
        },
        {
            "user_id": "demo_2",
            "user_name": "Mia",
            "message": "周末约会想要甜一点，但不要显手黑",
            "recommended_designs": ["奶油粉晕染", "豆沙蝴蝶结"],
            "top_tags": ["甜美", "晕染", "显白"],
            "created_at": now,
        },
        {
            "user_id": "demo_3",
            "user_name": "阿青",
            "message": "短甲日常款帮我三选一",
            "recommended_designs": ["短甲猫眼", "裸粉渐变", "低饱和法式"],
            "top_tags": ["短甲", "日常", "猫眼"],
            "created_at": now,
        },
    ]


def _pick_recommendations(db: Session, message: str, limit: int = 4) -> list[dict[str, Any]]:
    designs = db.query(models.NailDesign).filter(models.NailDesign.status == "active").order_by(
        models.NailDesign.is_hot.desc(),
        models.NailDesign.try_on_count.desc(),
        models.NailDesign.favorite_count.desc(),
    ).limit(80).all()
    designs = filter_servable_designs(designs)

    ranked = sorted(designs, key=lambda design: _recommendation_score(design, message), reverse=True)[:limit]
    return [
        {
            "id": design.id,
            "name": design.name,
            "image_url": design.image_url,
            "reason": _recommendation_reason(design, message),
            "style_tags": list(design_to_effective_tags(design).get("style_tags") or [])[:3],
        }
        for design in ranked
    ]


def _query_terms(message: str) -> list[str]:
    message_lower = message.lower()
    terms: list[str] = []
    for trigger, values in QUERY_INTENT_TERMS.items():
        if trigger.lower() in message_lower:
            terms.extend(values)

    compact_message = message.strip()
    for value in QUERY_INTENT_TERMS.values():
        for term in value:
            if term and term in compact_message:
                terms.append(term)

    seen: set[str] = set()
    unique_terms: list[str] = []
    for term in terms:
        normalized = term.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_terms.append(normalized)
    return unique_terms


def _recommendation_score(design: models.NailDesign, message: str) -> tuple[int, int, int, int]:
    tags = design_to_effective_tags(design)
    style_tags = set(tags.get("style_tags") or [])
    color_tags = set(tags.get("color_tags") or [])
    scene_tags = set(tags.get("scene_tags") or [])
    length = tags.get("length") or ""
    shape = tags.get("shape") or ""
    description = str(tags.get("description") or "")
    name = str(design.name or "")
    semantic_score = 0

    for term in _query_terms(message):
        if term in style_tags:
            semantic_score += 32
        if term in scene_tags:
            semantic_score += 30
        if term in color_tags:
            semantic_score += 24
        if term == length:
            semantic_score += 36
        if term == shape:
            semantic_score += 18
        if term in name:
            semantic_score += 16
        if term in description:
            semantic_score += 10

    direct_message = message.strip()
    all_values = [name, description, length, shape, *style_tags, *color_tags, *scene_tags]
    direct_matches = sum(1 for value in all_values if value and value in direct_message)
    semantic_score += direct_matches * 14

    popularity_score = int(bool(design.is_hot)) * 4 + int(bool(design.is_new)) * 3 + min(design.try_on_count, 120) // 30
    business_score = min(design.favorite_count, 80) // 20 + min(design.booking_count, 40) // 20
    return semantic_score, popularity_score, business_score, int(design.id or 0)


def _recommendation_reason(design: models.NailDesign, message: str) -> str:
    tags = design_to_effective_tags(design)
    style_tags = list(tags.get("style_tags") or [])
    scene_tags = list(tags.get("scene_tags") or [])
    if any(word in message for word in ["通勤", "上班", "日常"]):
        return "偏日常耐看，适合低风险先试戴。"
    if any(word in message for word in ["约会", "甜", "显白"]):
        return "氛围更柔和，适合想要甜美和显白效果。"
    if scene_tags:
        return f"适合{scene_tags[0]}场景，风格辨识度比较明确。"
    if style_tags:
        return f"{style_tags[0]}风格热度较高，适合作为第一轮试戴候选。"
    return "近期互动表现稳定，适合加入候选清单对比。"


def _fallback_answer(message: str, recommendations: list[dict[str, Any]]) -> str:
    first = recommendations[0]["name"] if recommendations else "热门款式"
    if any(word in message for word in ["显白", "肤色", "黑黄皮"]):
        return f"我是{PERSONA_NAME}。如果你优先想显白，我建议先从低饱和、裸粉、法式或带一点亮片的款开始，第一款可以试 {first}。"
    if any(word in message for word in ["通勤", "上班", "日常"]):
        return f"我是{PERSONA_NAME}。通勤场景别选太复杂的立体装饰，先试干净耐看的短甲或法式，{first} 可以作为第一候选。"
    return f"我是{PERSONA_NAME}。我会按你的场景、肤色倾向和风格强度帮你缩小选择。先把 {first} 放进第一轮试戴，再用候选清单做对比。"


def _llm_answer(message: str, recommendations: list[dict[str, Any]]) -> tuple[str, str]:
    client = DeepSeekClient()
    if not client.available:
        return _fallback_answer(message, recommendations), "low"
    try:
        response = client.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"你是甲感 NailMind 的用户端美甲试戴助手，名字叫{PERSONA_NAME}。"
                        "人设：审美敏锐、像懂美甲的朋友，不油腻，不夸张。"
                        "任务：根据用户表达的场景、肤色、风格偏好，给出简短建议，并引导用户去试戴或加入候选。"
                        "不要编造不存在的款式，只能引用提供的推荐列表。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"用户问题：{message}\n可推荐款式：{recommendations}",
                },
            ],
            max_tokens=600,
        )
        return response["choices"][0]["message"].get("content") or _fallback_answer(message, recommendations), "high"
    except Exception:
        return _fallback_answer(message, recommendations), "low"


def _record_event(user: models.User, message: str, recommendations: list[dict[str, Any]]) -> None:
    tags = Counter(tag for item in recommendations for tag in item.get("style_tags", []))
    _RECENT_EVENTS.appendleft(
        {
            "user_id": user.id,
            "user_name": user.nickname or f"用户{str(user.phone)[-4:]}",
            "message": message,
            "recommended_designs": [item["name"] for item in recommendations],
            "top_tags": [tag for tag, _count in tags.most_common(3)],
            "created_at": datetime.now().isoformat(),
        }
    )


@router.post("/chat", response_model=schemas.ConsumerAssistantChatResponse)
def chat_with_consumer_assistant(
    request: schemas.ConsumerAssistantChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_consumer),
):
    recommendations = _pick_recommendations(db, request.message)
    answer, confidence = _llm_answer(request.message, recommendations)
    _record_event(current_user, request.message, recommendations)
    return {
        "persona": PERSONA_NAME,
        "answer": answer,
        "recommendations": recommendations,
        "chips": ["显白通勤款", "约会甜美款", "短甲日常", "帮我三选一"],
        "conversation_id": request.conversation_id or f"consumer_{current_user.id}_{uuid4().hex[:8]}",
        "confidence": confidence,
    }


@router.get("/insights")
def get_consumer_assistant_insights(_operator: models.User = Depends(require_operator)):
    events = list(_RECENT_EVENTS) or _demo_events()
    tag_counts = Counter(tag for event in events for tag in event.get("top_tags", []))
    return {
        "total_messages": len(events),
        "active_users": len({event["user_id"] for event in events}),
        "top_intents": [
            {"name": name, "count": count}
            for name, count in _infer_intents(events).most_common(5)
        ],
        "top_tags": [
            {"name": tag, "count": count}
            for tag, count in tag_counts.most_common(6)
        ],
        "recent_messages": events[:12],
    }


def _infer_intents(events: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for event in events:
        message = event.get("message", "")
        if any(word in message for word in ["显白", "肤色", "黑黄皮"]):
            counter["显白与肤色适配"] += 1
        elif any(word in message for word in ["通勤", "上班", "日常"]):
            counter["日常通勤"] += 1
        elif any(word in message for word in ["约会", "甜", "拍照"]):
            counter["约会拍照"] += 1
        elif any(word in message for word in ["对比", "三选一", "选哪个"]):
            counter["决策对比"] += 1
        else:
            counter["泛选款咨询"] += 1
    return counter
