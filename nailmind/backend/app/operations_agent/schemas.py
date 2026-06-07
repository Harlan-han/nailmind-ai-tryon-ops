"""Internal schemas for the operations assistant agent."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AssistantEvidence(BaseModel):
    label: str
    value: str
    source: str


class AssistantAction(BaseModel):
    title: str
    reason: str
    priority: str = "medium"
    risk: Optional[str] = None
    requires_confirmation: bool = True


class ToolTrace(BaseModel):
    tool: str
    status: str
    summary: Optional[str] = None


class AssistantResponse(BaseModel):
    answer: str
    evidence: List[AssistantEvidence] = Field(default_factory=list)
    recommended_actions: List[AssistantAction] = Field(default_factory=list)
    tool_trace: List[ToolTrace] = Field(default_factory=list)
    confidence: str = "medium"


class ToolResult(BaseModel):
    tool: str
    data: Dict[str, Any]

