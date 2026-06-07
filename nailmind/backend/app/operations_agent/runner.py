"""Operations assistant orchestration."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.operations_agent.llm_client import DeepSeekClient, parse_json_content
from app.operations_agent.schemas import AssistantAction, AssistantEvidence, AssistantResponse, ToolTrace
from app.operations_agent.tools import OperationsToolRegistry, get_tool_definitions


SYSTEM_PROMPT = """你是甲感 NailMind 的运营智能体。
你的职责是基于后端工具返回的真实数据，回答美甲运营问题并给出可执行建议。
规则：
1. 不要编造工具没有提供的数据。
2. 明确区分结论、证据和建议。
3. 所有执行动作都必须要求人工确认。
4. 输出必须是 JSON，对象字段为 answer、evidence、recommended_actions、confidence。
"""


class OperationsAgentRunner:
    def __init__(
        self,
        llm_client: Optional[DeepSeekClient] = None,
        tools: Optional[OperationsToolRegistry] = None,
    ) -> None:
        self.llm_client = llm_client or DeepSeekClient()
        self.tools = tools or OperationsToolRegistry()

    def chat(self, message: str, db: Session, context: Optional[Dict[str, Any]] = None) -> AssistantResponse:
        if not self.llm_client or not getattr(self.llm_client, "available", False):
            return self._fallback_response(message, db, context)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self._build_user_content(message, context)},
        ]
        tool_trace: List[ToolTrace] = []
        tool_results: List[Dict[str, Any]] = []

        try:
            first = self.llm_client.create_chat_completion(
                messages=messages,
                tools=get_tool_definitions(),
                tool_choice="auto",
            )
            assistant_message = first["choices"][0]["message"]
            tool_calls = assistant_message.get("tool_calls") or []

            if not tool_calls:
                tool_result = self.tools.execute("get_action_plan", {}, db)
                tool_trace.append(ToolTrace(tool="get_action_plan", status="success", summary="fallback tool"))
                return self._summarize_with_tools(message, [tool_result], tool_trace)

            messages.append(assistant_message)
            for call in tool_calls:
                function = call.get("function") or {}
                tool_name = function.get("name")
                arguments = self._parse_arguments(function.get("arguments"))
                if not tool_name:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id"),
                            "content": json.dumps({"error": "Missing tool name"}, ensure_ascii=False),
                        }
                    )
                    continue
                try:
                    result = self.tools.execute(tool_name, arguments, db)
                    tool_results.append(result)
                    tool_trace.append(ToolTrace(tool=tool_name, status="success"))
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id"),
                            "content": json.dumps(result, ensure_ascii=False, default=str),
                        }
                    )
                except Exception as exc:
                    tool_trace.append(ToolTrace(tool=tool_name, status="failed", summary=str(exc)))
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id"),
                            "content": json.dumps({"error": str(exc)}, ensure_ascii=False),
                        }
                    )

            messages.append(
                {
                    "role": "user",
                    "content": "请基于工具结果输出严格 JSON，不要使用 Markdown。",
                }
            )
            try:
                final = self.llm_client.create_chat_completion(
                    messages=messages,
                    tools=get_tool_definitions(),
                    tool_choice="none",
                    response_format={"type": "json_object"},
                    max_tokens=4096,
                )
            except Exception as exc:
                tool_trace.append(ToolTrace(tool="deepseek_summary", status="fallback", summary=str(exc)))
                response = self._summarize_with_tools(message, tool_results, tool_trace)
                response.confidence = "low"
                return response
            content = final["choices"][0]["message"].get("content") or ""
            parsed = parse_json_content(content)
            if not parsed and content:
                try:
                    repair = self.llm_client.create_chat_completion(
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "你是 JSON 修复器。只输出一个合法 JSON 对象，不要 Markdown，"
                                    "字段必须包含 answer、evidence、recommended_actions、confidence。"
                                ),
                            },
                            {
                                "role": "user",
                                "content": json.dumps(
                                    {
                                        "raw_model_output": content,
                                        "tool_results": tool_results,
                                        "schema": {
                                            "answer": "string",
                                            "evidence": [{"label": "string", "value": "string", "source": "string"}],
                                            "recommended_actions": [
                                                {
                                                    "title": "string",
                                                    "reason": "string",
                                                    "priority": "high|medium|low",
                                                    "risk": "string|null",
                                                    "requires_confirmation": True,
                                                }
                                            ],
                                            "confidence": "high|medium|low",
                                        },
                                    },
                                    ensure_ascii=False,
                                    default=str,
                                ),
                            },
                        ],
                        response_format={"type": "json_object"},
                        max_tokens=2048,
                    )
                    repair_content = repair["choices"][0]["message"].get("content") or ""
                    parsed = parse_json_content(repair_content)
                    if parsed:
                        tool_trace.append(
                            ToolTrace(
                                tool="deepseek_parse",
                                status="success",
                                summary="repaired non-json final response",
                            )
                        )
                except Exception as exc:
                    tool_trace.append(ToolTrace(tool="deepseek_parse", status="fallback", summary=str(exc)))
            if not parsed:
                tool_trace.append(
                    ToolTrace(
                        tool="deepseek_parse",
                        status="failed",
                        summary="final response was not valid JSON",
                    )
                )
                response = self._summarize_with_tools(message, tool_results, tool_trace)
                if content:
                    response.answer = f"{content}\n\n我已用工具结果补充了结构化证据和行动建议。"
                response.confidence = "low"
                return response
            return self._normalize_response(parsed, tool_trace)
        except Exception as exc:
            response = self._fallback_response(message, db, context)
            response.tool_trace.append(ToolTrace(tool="deepseek", status="fallback", summary=str(exc)))
            response.confidence = "low"
            return response

    def _summarize_with_tools(
        self,
        message: str,
        tool_results: List[Dict[str, Any]],
        tool_trace: List[ToolTrace],
    ) -> AssistantResponse:
        evidence = self._build_evidence_from_tool_results(tool_results)
        actions = self._build_actions_from_tool_results(tool_results)
        if not evidence:
            evidence = [
                AssistantEvidence(label=result["tool"], value="已读取运营数据", source=result["tool"])
                for result in tool_results
            ]
        if not actions:
            actions = [
                AssistantAction(
                    title="查看行动计划并人工确认推荐位调整",
                    reason="当前回答来自规则型运营工具，适合作为人工运营决策输入。",
                    priority="medium",
                    risk="需要结合库存、门店承接能力和活动节奏确认。",
                )
            ]

        evidence_summary = "；".join(f"{item.label}: {item.value}" for item in evidence[:3])
        return AssistantResponse(
            answer=f"我已根据当前运营数据处理你的问题：{message}。{evidence_summary}",
            evidence=evidence,
            recommended_actions=actions,
            tool_trace=tool_trace,
            confidence="medium",
        )

    def _build_evidence_from_tool_results(self, tool_results: List[Dict[str, Any]]) -> List[AssistantEvidence]:
        evidence: List[AssistantEvidence] = []
        for result in tool_results:
            tool = str(result.get("tool") or "operations_tool")
            data = result.get("data") or {}
            if tool == "get_overview":
                evidence.extend(self._overview_evidence(data, tool))
            elif tool == "get_funnel":
                evidence.extend(self._funnel_evidence(data, tool))
            elif tool == "get_daily_report":
                evidence.extend(self._daily_report_evidence(data, tool))
            elif tool == "get_weekly_report":
                evidence.extend(self._weekly_report_evidence(data, tool))
            elif tool == "get_recommendation_slot_plan":
                evidence.extend(self._recommendation_slot_evidence(data, tool))
            elif tool == "get_hot_candidates":
                evidence.extend(self._items_evidence(data, tool, "爆款候选"))
            elif tool == "get_cold_designs":
                evidence.extend(self._items_evidence(data, tool, "低效款式"))
            elif tool in {
                "find_high_tryon_low_booking_designs",
                "find_high_favorite_low_booking_designs",
                "find_converted_tryon_images",
            }:
                evidence.extend(self._items_evidence(data, tool, "转化信号"))
            elif tool in {"analyze_design_performance", "explain_hot_design"}:
                evidence.extend(self._design_evidence(data, tool))
            elif tool == "get_ai_insights":
                evidence.extend(self._insight_evidence(data, tool))
            elif tool == "get_trends":
                evidence.extend(self._trend_evidence(data, tool))
            elif tool == "get_suggestions":
                evidence.extend(self._items_evidence(data, tool, "待处理建议"))
            elif tool == "get_booking_followups":
                evidence.extend(self._booking_followup_evidence(data, tool))
        return evidence[:12]

    def _build_actions_from_tool_results(self, tool_results: List[Dict[str, Any]]) -> List[AssistantAction]:
        actions: List[AssistantAction] = []
        for result in tool_results:
            tool = str(result.get("tool") or "")
            data = result.get("data") or {}
            if tool == "get_action_plan":
                actions.extend(self._actions_from_action_plan(data))
            elif tool == "get_daily_report":
                actions.extend(self._actions_from_daily_report(data))
            elif tool == "get_weekly_report":
                actions.extend(self._actions_from_action_plan(data))
            elif tool == "get_recommendation_slot_plan":
                actions.extend(self._actions_from_action_plan(data))
            elif tool == "get_hot_candidates":
                actions.extend(self._actions_from_items(data, "上调高潜款推荐位", "近期增长和试戴信号更强，适合进入首页推荐位。", "high"))
            elif tool == "get_cold_designs":
                actions.extend(self._actions_from_items(data, "下调低效款曝光", "曝光或展示占用资源但转化偏弱，建议先降低推荐位并复盘标签。", "medium"))
            elif tool == "find_high_tryon_low_booking_designs":
                actions.extend(self._actions_from_items(data, "修复试戴到预约断层", "用户已经产生试戴兴趣，但预约意向没有跟上，需要优化预约入口、价格说明或门店案例。", "high"))
            elif tool == "find_high_favorite_low_booking_designs":
                actions.extend(self._actions_from_items(data, "跟进高收藏低预约款", "收藏代表强兴趣，适合用限时预约、客服触达或活动提醒推动转化。", "medium"))
            elif tool == "get_booking_followups":
                actions.extend(self._booking_followup_actions(data))
        return actions[:6]

    def _overview_evidence(self, data: Dict[str, Any], source: str) -> List[AssistantEvidence]:
        trending = data.get("trending_styles") or []
        top_style = ""
        if trending and isinstance(trending[0], dict):
            top_style = f"，热门风格 {trending[0].get('style')} {trending[0].get('count')} 次"
        return [
            AssistantEvidence(
                label="今日核心数据",
                value=(
                    f"今日试戴 {data.get('today_try_ons', 0)}，"
                    f"收藏 {data.get('today_favorites', 0)}，"
                    f"今日预约 {data.get('today_booking_intents', 0)}，"
                    f"热门款 {data.get('hot_designs_count', 0)}{top_style}"
                ),
                source=source,
            )
        ]

    def _funnel_evidence(self, data: Dict[str, Any], source: str) -> List[AssistantEvidence]:
        metrics = data.get("metrics") or data
        if not isinstance(metrics, dict):
            return []
        parts = []
        for key in ["views", "try_ons", "favorites", "bookings"]:
            if key in metrics:
                parts.append(f"{key}: {metrics[key]}")
        for key in ["view_to_tryon_rate", "tryon_to_favorite_rate", "favorite_to_booking_rate", "overall_conversion_rate"]:
            if key in metrics:
                parts.append(f"{key}: {metrics[key]}")
        return [AssistantEvidence(label="转化漏斗", value="，".join(parts) or str(metrics), source=source)]

    def _daily_report_evidence(self, data: Dict[str, Any], source: str) -> List[AssistantEvidence]:
        evidence: List[AssistantEvidence] = []
        summary = data.get("summary")
        if summary:
            evidence.append(AssistantEvidence(label="日报摘要", value=str(summary), source=source))
        for index, highlight in enumerate(data.get("highlights") or []):
            evidence.append(AssistantEvidence(label=f"日报亮点 {index + 1}", value=str(highlight), source=source))
        for index, alert in enumerate(data.get("alerts") or []):
            evidence.append(AssistantEvidence(label=f"日报预警 {index + 1}", value=str(alert), source=source))
        return evidence

    def _weekly_report_evidence(self, data: Dict[str, Any], source: str) -> List[AssistantEvidence]:
        evidence: List[AssistantEvidence] = []
        summary = data.get("summary")
        metrics = data.get("metrics") or {}
        if summary:
            evidence.append(AssistantEvidence(label="周报摘要", value=str(summary), source=source))
        if metrics:
            evidence.append(
                AssistantEvidence(
                    label="周报核心指标",
                    value=(
                        f"试戴 {metrics.get('try_ons', 0)}，"
                        f"收藏 {metrics.get('favorites', 0)}，"
                        f"预约 {metrics.get('bookings', 0)}，"
                        f"预约率 {metrics.get('try_on_to_booking_rate', 0)}%"
                    ),
                    source=source,
                )
            )
        top_styles = data.get("top_styles") or []
        if top_styles:
            evidence.append(
                AssistantEvidence(
                    label="本周领先风格",
                    value="、".join(f"{item.get('tag')} {item.get('try_ons')} 次" for item in top_styles[:5]),
                    source=source,
                )
            )
        return evidence

    def _recommendation_slot_evidence(self, data: Dict[str, Any], source: str) -> List[AssistantEvidence]:
        recommendations = data.get("recommendations") or []
        if not recommendations:
            return []
        parts = []
        for item in recommendations[:5]:
            design = item.get("design") or {}
            parts.append(
                f"{item.get('slot_action', 'observe')}：{design.get('name') or item.get('action')}，"
                f"score={item.get('score', 0)}"
            )
        return [AssistantEvidence(label="推荐位计划", value="；".join(parts), source=source)]

    def _items_evidence(self, data: Dict[str, Any], source: str, label: str) -> List[AssistantEvidence]:
        items = data.get("items") if isinstance(data, dict) else []
        if items is None and isinstance(data, list):
            items = data
        if not items:
            return []
        values = [self._item_title(item) for item in items[:5]]
        return [AssistantEvidence(label=label, value="；".join(values), source=source)]

    def _booking_followup_evidence(self, data: Dict[str, Any], source: str) -> List[AssistantEvidence]:
        items = data.get("items") if isinstance(data, dict) else []
        if not items:
            return []

        status_count: Dict[str, int] = {}
        for item in items:
            status = str(item.get("status") or "pending")
            status_count[status] = status_count.get(status, 0) + 1

        top_items = []
        for item in items[:5]:
            top_items.append(
                f"{item.get('user_name') or '用户'} / {item.get('phone') or '无手机号'} / "
                f"{item.get('design_name') or '未知款式'} / {item.get('status') or 'pending'}"
            )

        return [
            AssistantEvidence(
                label="预约跟进队列",
                value=f"共 {len(items)} 条，状态分布 {self._compact_value(status_count)}",
                source=source,
            ),
            AssistantEvidence(
                label="优先联系客户",
                value="；".join(top_items),
                source=source,
            ),
        ]

    def _design_evidence(self, data: Dict[str, Any], source: str) -> List[AssistantEvidence]:
        design = data.get("design") or {}
        signals = data.get("signals") or {}
        rates = data.get("rates") or {}
        name = design.get("name") or f"款式 {design.get('id', '')}".strip()
        parts = [name]
        for key in ["try_on_count", "favorite_count", "booking_count"]:
            if key in signals:
                parts.append(f"{key}: {signals[key]}")
        for key in ["try_on_to_booking_rate", "favorite_to_booking_rate"]:
            if key in rates:
                parts.append(f"{key}: {rates[key]}")
        return [AssistantEvidence(label="单款表现", value="，".join(parts), source=source)]

    def _insight_evidence(self, data: Dict[str, Any], source: str) -> List[AssistantEvidence]:
        evidence: List[AssistantEvidence] = []
        for key in ["summary", "trend_prediction", "anomalies", "inventory_recommendations"]:
            value = data.get(key)
            if value:
                evidence.append(AssistantEvidence(label=key, value=self._compact_value(value), source=source))
        return evidence

    def _trend_evidence(self, data: Dict[str, Any], source: str) -> List[AssistantEvidence]:
        style_distribution = data.get("style_distribution") or {}
        color_distribution = data.get("color_distribution") or {}
        period = data.get("period", "recent")
        parts = [f"周期 {period}"]
        if style_distribution:
            parts.append("风格 " + self._top_distribution(style_distribution))
        if color_distribution:
            parts.append("颜色 " + self._top_distribution(color_distribution))
        return [AssistantEvidence(label="趋势分布", value="；".join(parts), source=source)]

    def _actions_from_action_plan(self, data: Dict[str, Any]) -> List[AssistantAction]:
        raw_actions = data.get("actions") or data.get("action_items") or data.get("recommendations") or []
        return [self._action_from_raw(item, "行动计划建议") for item in raw_actions[:6] if isinstance(item, dict)]

    def _actions_from_daily_report(self, data: Dict[str, Any]) -> List[AssistantAction]:
        raw_actions = data.get("recommendations") or []
        return [self._action_from_raw(item, "日报建议") for item in raw_actions[:4] if isinstance(item, dict)]

    def _actions_from_items(self, data: Dict[str, Any], title: str, reason: str, priority: str) -> List[AssistantAction]:
        items = data.get("items") if isinstance(data, dict) else []
        if not items:
            return []
        names = "、".join(self._item_title(item) for item in items[:3])
        return [
            AssistantAction(
                title=f"{title}：{names}",
                reason=reason,
                priority=priority,
                risk="执行前需要确认库存、门店承接能力和当前活动节奏。",
                requires_confirmation=True,
            )
        ]

    def _booking_followup_actions(self, data: Dict[str, Any]) -> List[AssistantAction]:
        items = data.get("items") if isinstance(data, dict) else []
        if not items:
            return []
        pending = [item for item in items if item.get("status") == "pending"]
        contacted = [item for item in items if item.get("status") == "contacted"]
        if pending:
            names = "、".join(
                f"{item.get('user_name') or '用户'}-{item.get('design_name') or '款式'}"
                for item in pending[:3]
            )
            return [
                AssistantAction(
                    title=f"优先联系待确认预约：{names}",
                    reason="这些客户已经从试戴结果页留下手机号，是当前最接近到店转化的真实意向。",
                    priority="high",
                    risk="联系前需要确认门店可约时段、价格说明和款式服务能力。",
                    requires_confirmation=True,
                )
            ]
        if contacted:
            names = "、".join(
                f"{item.get('user_name') or '用户'}-{item.get('design_name') or '款式'}"
                for item in contacted[:3]
            )
            return [
                AssistantAction(
                    title=f"推进已联系客户确认到店：{names}",
                    reason="客户已被触达但还没有确认到店，适合补充档期、价格和案例信息。",
                    priority="medium",
                    risk="避免过度打扰，同一客户短时间内只做一次明确跟进。",
                    requires_confirmation=True,
                )
            ]
        return []

    def _action_from_raw(self, item: Dict[str, Any], fallback_title: str) -> AssistantAction:
        return AssistantAction(
            title=str(item.get("title") or item.get("action") or fallback_title),
            reason=str(item.get("reason") or item.get("description") or item.get("expected_impact") or "来自运营工具的行动建议。"),
            priority=str(item.get("priority") or "medium"),
            risk=item.get("risk") or "执行前需要人工确认。",
            requires_confirmation=bool(item.get("requires_confirmation", True)),
        )

    def _item_title(self, item: Any) -> str:
        if not isinstance(item, dict):
            return str(item)
        design = item.get("design") if isinstance(item.get("design"), dict) else {}
        name = design.get("name") or item.get("design_name") or item.get("name") or item.get("title")
        design_id = design.get("id") or item.get("design_id") or item.get("id")
        metrics = []
        for key in ["recent_try_ons", "try_on_count", "favorite_count", "booking_count", "growth_rate", "conversion_rate"]:
            if key in item:
                metrics.append(f"{key}={item[key]}")
        label = str(name or (f"款式 {design_id}" if design_id else "款式"))
        return f"{label}（{', '.join(metrics)}）" if metrics else label

    def _compact_value(self, value: Any) -> str:
        if isinstance(value, list):
            return "；".join(self._compact_value(item) for item in value[:5])
        if isinstance(value, dict):
            return "，".join(f"{key}: {self._compact_value(val)}" for key, val in list(value.items())[:6])
        return str(value)

    def _top_distribution(self, distribution: Dict[str, Any]) -> str:
        items = sorted(distribution.items(), key=lambda item: item[1], reverse=True)[:5]
        return "、".join(f"{key} {value}" for key, value in items)

    def _fallback_response(
        self,
        message: str,
        db: Session,
        context: Optional[Dict[str, Any]],
    ) -> AssistantResponse:
        selected_tools = self._select_fallback_tools(message, context)
        tool_results: List[Dict[str, Any]] = []
        tool_trace: List[ToolTrace] = []
        for tool_name, args in selected_tools:
            try:
                result = self.tools.execute(tool_name, args, db)
                tool_results.append(result)
                tool_trace.append(ToolTrace(tool=tool_name, status="success"))
            except Exception as exc:
                tool_trace.append(ToolTrace(tool=tool_name, status="failed", summary=str(exc)))

        response = self._summarize_with_tools(message, tool_results, tool_trace)
        if not getattr(self.llm_client, "available", False):
            response.answer = "DeepSeek API Key 未配置，当前使用规则型运营助手返回基础建议。"
            response.confidence = "low"
        return response

    def _select_fallback_tools(
        self,
        message: str,
        context: Optional[Dict[str, Any]],
    ) -> List[tuple[str, Dict[str, Any]]]:
        days = (context or {}).get("days", 30)
        design_id_match = re.search(r"(?:款式|设计|design)\s*#?\s*(\d+)", message, re.IGNORECASE)
        if design_id_match:
            design_id = int(design_id_match.group(1))
            if any(keyword in message for keyword in ["热", "火", "爆", "为什么"]):
                return [("explain_hot_design", {"design_id": design_id})]
            return [("analyze_design_performance", {"design_id": design_id})]

        if all(keyword in message for keyword in ["试戴", "预约"]) and any(
            keyword in message for keyword in ["低", "差", "少", "弱", "没有", "哪些"]
        ):
            return [("find_high_tryon_low_booking_designs", {"limit": 10})]
        if all(keyword in message for keyword in ["收藏", "预约"]) and any(
            keyword in message for keyword in ["低", "差", "少", "弱", "没有", "哪些"]
        ):
            return [("find_high_favorite_low_booking_designs", {"limit": 10})]
        if all(keyword in message for keyword in ["试戴", "预约"]) and any(
            keyword in message for keyword in ["图片", "图", "转化", "带来"]
        ):
            return [("find_converted_tryon_images", {"limit": 10})]
        if any(keyword in message for keyword in ["预约客户", "预约跟进", "跟进客户", "联系客户", "到店", "待确认"]):
            return [("get_booking_followups", {"status": "pending", "limit": 10}), ("get_funnel", {"days": days})]
        if any(keyword in message for keyword in ["周报", "本周", "周复盘"]):
            return [("get_weekly_report", {"days": 7})]
        if any(keyword in message for keyword in ["推荐位", "调整建议", "推荐调整", "上调", "下调"]):
            return [("get_recommendation_slot_plan", {"limit": 5})]
        if any(keyword in message for keyword in ["日报", "报告", "复盘"]):
            return [("get_daily_report", {}), ("get_action_plan", {})]
        if any(keyword in message for keyword in ["冷", "下推荐", "低效", "下架"]):
            return [("get_cold_designs", {}), ("get_funnel", {"days": days})]
        if any(keyword in message for keyword in ["推", "爆款", "热门", "增长"]):
            return [("get_hot_candidates", {"limit": 5}), ("get_trends", {"days": days})]
        if any(keyword in message for keyword in ["异常", "问题", "风险"]):
            return [("get_ai_insights", {}), ("get_action_plan", {})]
        return [("get_overview", {}), ("get_action_plan", {})]

    def _build_user_content(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        return json.dumps(
            {
                "question": message,
                "context": context or {},
                "required_output": {
                    "answer": "string",
                    "evidence": [{"label": "string", "value": "string", "source": "string"}],
                    "recommended_actions": [
                        {
                            "title": "string",
                            "reason": "string",
                            "priority": "high|medium|low",
                            "risk": "string",
                            "requires_confirmation": True,
                        }
                    ],
                    "confidence": "high|medium|low",
                },
            },
            ensure_ascii=False,
        )

    def _parse_arguments(self, raw_arguments: Any) -> Dict[str, Any]:
        if isinstance(raw_arguments, dict):
            return raw_arguments
        if not raw_arguments:
            return {}
        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _normalize_response(self, parsed: Dict[str, Any], tool_trace: List[ToolTrace]) -> AssistantResponse:
        evidence = [
            AssistantEvidence(
                label=str(item.get("label", "证据")),
                value=str(item.get("value", "")),
                source=str(item.get("source", "operations_agent")),
            )
            for item in parsed.get("evidence", [])
            if isinstance(item, dict)
        ]
        actions = [
            AssistantAction(
                title=str(item.get("title", "运营建议")),
                reason=str(item.get("reason", "")),
                priority=str(item.get("priority", "medium")),
                risk=item.get("risk"),
                requires_confirmation=bool(item.get("requires_confirmation", True)),
            )
            for item in parsed.get("recommended_actions", [])
            if isinstance(item, dict)
        ]
        return AssistantResponse(
            answer=str(parsed.get("answer") or "已生成运营分析。"),
            evidence=evidence,
            recommended_actions=actions,
            tool_trace=tool_trace,
            confidence=str(parsed.get("confidence") or "medium"),
        )
