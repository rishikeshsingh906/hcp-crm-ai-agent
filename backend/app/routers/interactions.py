from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.agent.tools import make_log_interaction, make_edit_interaction, make_check_compliance

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.get("/", response_model=list[schemas.InteractionOut])
def list_interactions(hcp_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Interaction)
    if hcp_id:
        q = q.filter_by(hcp_id=hcp_id)
    return q.order_by(models.Interaction.interaction_date.desc()).all()


@router.get("/{interaction_id}", response_model=schemas.InteractionOut)
def get_interaction(interaction_id: int, db: Session = Depends(get_db)):
    interaction = db.query(models.Interaction).filter_by(id=interaction_id).first()
    if not interaction:
        raise HTTPException(404, "Interaction not found")
    return interaction


@router.post("/", response_model=schemas.InteractionOut)
def create_interaction(payload: schemas.InteractionCreate, db: Session = Depends(get_db)):
    """Structured-form submission path. Still routes through the log_interaction
    LangGraph tool so the LLM performs summarization/entity extraction, and then
    immediately runs a compliance check — the same pipeline the chat path uses."""
    tool = make_log_interaction(db)
    result = tool.func(
        hcp_id=payload.hcp_id,
        raw_notes=payload.raw_notes,
        channel=payload.channel or "in_person",
        rep_name=payload.rep_name or "Field Rep",
        interaction_date=payload.interaction_date.isoformat() if payload.interaction_date else None,
        source=payload.source or "form",
    )
    if "error" in result:
        raise HTTPException(400, result["error"])

    compliance_tool = make_check_compliance(db)
    compliance_tool.func(interaction_id=result["interaction_id"])

    return db.query(models.Interaction).filter_by(id=result["interaction_id"]).first()


@router.patch("/{interaction_id}", response_model=schemas.InteractionOut)
def edit_interaction(interaction_id: int, payload: schemas.InteractionUpdate, db: Session = Depends(get_db)):
    tool = make_edit_interaction(db)
    result = tool.func(
        interaction_id=interaction_id,
        raw_notes=payload.raw_notes,
        summary=payload.summary,
        topics_discussed=payload.topics_discussed,
        sentiment=payload.sentiment,
        channel=payload.channel,
    )
    if "error" in result:
        raise HTTPException(404, result["error"])
    return db.query(models.Interaction).filter_by(id=interaction_id).first()


@router.delete("/{interaction_id}")
def delete_interaction(interaction_id: int, db: Session = Depends(get_db)):
    interaction = db.query(models.Interaction).filter_by(id=interaction_id).first()
    if not interaction:
        raise HTTPException(404, "Interaction not found")
    db.delete(interaction)
    db.commit()
    return {"ok": True}
