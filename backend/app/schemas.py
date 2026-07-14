from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class HCPBase(BaseModel):
    name: str
    specialty: Optional[str] = None
    institution: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    preferred_channel: Optional[str] = "in_person"
    notes: Optional[str] = None


class HCPCreate(HCPBase):
    pass


class HCPOut(HCPBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class InteractionCreate(BaseModel):
    hcp_id: int
    rep_name: Optional[str] = "Field Rep"
    channel: Optional[str] = "in_person"
    raw_notes: str
    interaction_date: Optional[datetime] = None
    source: Optional[str] = "form"


class InteractionUpdate(BaseModel):
    channel: Optional[str] = None
    raw_notes: Optional[str] = None
    summary: Optional[str] = None
    topics_discussed: Optional[List[str]] = None
    samples_distributed: Optional[List[Dict[str, Any]]] = None
    sentiment: Optional[str] = None
    interaction_date: Optional[datetime] = None


class InteractionOut(BaseModel):
    id: int
    hcp_id: int
    rep_name: str
    channel: str
    raw_notes: Optional[str]
    summary: Optional[str]
    topics_discussed: Optional[List[str]]
    samples_distributed: Optional[List[Dict[str, Any]]]
    sentiment: str
    compliance_flag: bool
    compliance_notes: Optional[str]
    interaction_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    source: str

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    hcp_id: Optional[int] = None
    active_interaction_id: Optional[int] = None
    rep_name: Optional[str] = "Field Rep"


class ChatResponse(BaseModel):
    reply: str
    tool_calls: List[Dict[str, Any]] = []
    interaction: Optional[InteractionOut] = None
