from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.agent.graph import run_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Drives the conversational Log Interaction path. The full message history
    is sent each turn (LangGraph itself is stateless across HTTP requests, so
    the frontend/Redux store is the source of truth for conversation state).
    An hcp_id, if selected in the UI, is prepended as context so the agent
    doesn't need to ask for it again.
    """
    messages = [m.model_dump() for m in payload.messages]
    if payload.hcp_id:
        messages = [
            {"role": "user", "content": f"[context: hcp_id={payload.hcp_id}, rep_name={payload.rep_name}]"}
        ] + messages

    result = run_agent(db, messages)
    return ChatResponse(reply=result["reply"], tool_calls=result["tool_calls"])
