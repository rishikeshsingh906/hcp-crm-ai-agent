"""
The 5 tools available to the LangGraph HCP agent.

Each tool is built as a closure over a live SQLAlchemy session so it can
read/write the CRM database inside a single request's agent run.

1. log_interaction       - creates a new interaction record from freeform
                            text, using the LLM to summarize + extract
                            entities (topics, samples, sentiment).
2. edit_interaction       - patches an existing interaction (e.g. the rep
                            corrects the record after reviewing the
                            AI-generated summary).
3. get_hcp_profile        - looks up an HCP's profile + recent interaction
                            history, so the agent has context before
                            logging or summarizing.
4. schedule_followup      - creates a follow-up task/reminder tied to an
                            interaction (e.g. "send study X in 2 weeks").
5. check_compliance       - runs the LLM over the interaction notes to flag
                            language that may violate pharma compliance
                            rules (off-label promotion, gifting limits).
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.agent.llm import chat_completion, extract_json

COMPLIANCE_SYSTEM_PROMPT = (
    "You are a pharma compliance checker. Given HCP interaction notes, flag any "
    "mention of off-label drug use, promises of favors/kickbacks, exaggerated "
    "efficacy claims, or gifting above typical educational-item value. "
    "Return JSON: {\"flag\": bool, \"notes\": string}."
)

EXTRACTION_SYSTEM_PROMPT = (
    "You are an assistant for pharmaceutical field reps. Given raw notes or a chat "
    "transcript describing a visit with a healthcare professional (HCP), extract "
    "structured data. Return JSON with keys: "
    "\"summary\" (2-3 sentence professional summary), "
    "\"topics_discussed\" (list of strings: drugs/products/clinical topics raised), "
    "\"samples_distributed\" (list of objects {\"product\": str, \"qty\": int}, empty list if none), "
    "\"sentiment\" (one of positive, neutral, negative - the HCP's receptiveness)."
)


# ---------- 1. LOG INTERACTION ----------

class LogInteractionArgs(BaseModel):
    hcp_id: int = Field(..., description="ID of the HCP the interaction was with")
    raw_notes: str = Field(..., description="Freeform notes or chat transcript describing the visit")
    channel: str = Field("in_person", description="in_person | virtual | phone | email | conference")
    rep_name: str = Field("Field Rep", description="Name of the rep logging the interaction")
    interaction_date: Optional[str] = Field(None, description="ISO date of the visit, defaults to now")
    source: str = Field("form", description="'form' or 'chat' - how the interaction was captured")


def make_log_interaction(db: Session):
    def _run(hcp_id: int, raw_notes: str, channel: str = "in_person",
              rep_name: str = "Field Rep", interaction_date: Optional[str] = None,
              source: str = "form") -> Dict[str, Any]:
        extracted = extract_json(raw_notes, EXTRACTION_SYSTEM_PROMPT)

        interaction = models.Interaction(
            hcp_id=hcp_id,
            rep_name=rep_name,
            channel=channel,
            raw_notes=raw_notes,
            summary=extracted.get("summary", ""),
            topics_discussed=extracted.get("topics_discussed", []),
            samples_distributed=extracted.get("samples_distributed", []),
            sentiment=extracted.get("sentiment", "neutral"),
            interaction_date=datetime.fromisoformat(interaction_date) if interaction_date else datetime.utcnow(),
            source=source,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return {
            "interaction_id": interaction.id,
            "summary": interaction.summary,
            "topics_discussed": interaction.topics_discussed,
            "samples_distributed": interaction.samples_distributed,
            "sentiment": interaction.sentiment,
        }

    return StructuredTool.from_function(
        func=_run,
        name="log_interaction",
        description="Log a new HCP interaction from raw notes or a chat transcript. "
                     "Uses the LLM to auto-generate a summary, extract discussed topics, "
                     "samples distributed, and sentiment.",
        args_schema=LogInteractionArgs,
    )


# ---------- 2. EDIT INTERACTION ----------

class EditInteractionArgs(BaseModel):
    interaction_id: int = Field(..., description="ID of the interaction to edit")
    raw_notes: Optional[str] = Field(None, description="Replacement raw notes; if given, summary/topics are re-extracted")
    summary: Optional[str] = Field(None, description="Manually corrected summary")
    topics_discussed: Optional[List[str]] = Field(None, description="Manually corrected topic list")
    sentiment: Optional[str] = Field(None, description="Manually corrected sentiment")
    channel: Optional[str] = Field(None, description="Corrected channel")


def make_edit_interaction(db: Session):
    def _run(interaction_id: int, raw_notes: Optional[str] = None, summary: Optional[str] = None,
              topics_discussed: Optional[List[str]] = None, sentiment: Optional[str] = None,
              channel: Optional[str] = None) -> Dict[str, Any]:
        interaction = db.query(models.Interaction).filter_by(id=interaction_id).first()
        if not interaction:
            return {"error": f"No interaction found with id {interaction_id}"}

        if raw_notes:
            interaction.raw_notes = raw_notes
            extracted = extract_json(raw_notes, EXTRACTION_SYSTEM_PROMPT)
            interaction.summary = extracted.get("summary", interaction.summary)
            interaction.topics_discussed = extracted.get("topics_discussed", interaction.topics_discussed)
            interaction.samples_distributed = extracted.get("samples_distributed", interaction.samples_distributed)
            interaction.sentiment = extracted.get("sentiment", interaction.sentiment)
        if summary is not None:
            interaction.summary = summary
        if topics_discussed is not None:
            interaction.topics_discussed = topics_discussed
        if sentiment is not None:
            interaction.sentiment = sentiment
        if channel is not None:
            interaction.channel = channel

        interaction.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(interaction)
        return {
            "interaction_id": interaction.id,
            "summary": interaction.summary,
            "topics_discussed": interaction.topics_discussed,
            "sentiment": interaction.sentiment,
            "channel": interaction.channel,
        }

    return StructuredTool.from_function(
        func=_run,
        name="edit_interaction",
        description="Edit a previously logged interaction — either overwrite raw notes "
                     "(triggers re-summarization) or directly patch specific fields "
                     "like summary, topics, sentiment, or channel.",
        args_schema=EditInteractionArgs,
    )


# ---------- 3. GET HCP PROFILE ----------

class GetHcpProfileArgs(BaseModel):
    hcp_id: int = Field(..., description="ID of the HCP to look up")
    history_limit: int = Field(5, description="Number of recent past interactions to include")


def make_get_hcp_profile(db: Session):
    def _run(hcp_id: int, history_limit: int = 5) -> Dict[str, Any]:
        hcp = db.query(models.HCP).filter_by(id=hcp_id).first()
        if not hcp:
            return {"error": f"No HCP found with id {hcp_id}"}
        recent = (
            db.query(models.Interaction)
            .filter_by(hcp_id=hcp_id)
            .order_by(models.Interaction.interaction_date.desc())
            .limit(history_limit)
            .all()
        )
        return {
            "hcp": {
                "id": hcp.id, "name": hcp.name, "specialty": hcp.specialty,
                "institution": hcp.institution, "preferred_channel": hcp.preferred_channel,
                "notes": hcp.notes,
            },
            "recent_interactions": [
                {"id": i.id, "date": i.interaction_date.isoformat() if i.interaction_date else None,
                 "summary": i.summary, "sentiment": i.sentiment, "topics_discussed": i.topics_discussed}
                for i in recent
            ],
        }

    return StructuredTool.from_function(
        func=_run,
        name="get_hcp_profile",
        description="Fetch an HCP's profile (specialty, institution, preferences) plus "
                     "their recent interaction history, to give the agent context "
                     "before logging a new visit or answering questions about them.",
        args_schema=GetHcpProfileArgs,
    )


# ---------- 4. SCHEDULE FOLLOW-UP ----------

class ScheduleFollowUpArgs(BaseModel):
    interaction_id: int = Field(..., description="Interaction this follow-up is tied to")
    task: str = Field(..., description="What needs to happen, e.g. 'Send Phase III trial data'")
    due_date: str = Field(..., description="ISO date the follow-up is due")


def make_schedule_followup(db: Session):
    def _run(interaction_id: int, task: str, due_date: str) -> Dict[str, Any]:
        interaction = db.query(models.Interaction).filter_by(id=interaction_id).first()
        if not interaction:
            return {"error": f"No interaction found with id {interaction_id}"}
        followup = models.FollowUp(
            interaction_id=interaction_id,
            task=task,
            due_date=datetime.fromisoformat(due_date),
        )
        db.add(followup)
        db.commit()
        db.refresh(followup)
        return {"followup_id": followup.id, "task": followup.task, "due_date": due_date, "status": followup.status}

    return StructuredTool.from_function(
        func=_run,
        name="schedule_followup",
        description="Create a follow-up task/reminder linked to a logged interaction "
                     "(e.g. sending literature, scheduling the next visit).",
        args_schema=ScheduleFollowUpArgs,
    )


# ---------- 5. CHECK COMPLIANCE ----------

class CheckComplianceArgs(BaseModel):
    interaction_id: int = Field(..., description="Interaction to run a compliance check on")


def make_check_compliance(db: Session):
    def _run(interaction_id: int) -> Dict[str, Any]:
        interaction = db.query(models.Interaction).filter_by(id=interaction_id).first()
        if not interaction:
            return {"error": f"No interaction found with id {interaction_id}"}
        result = extract_json(interaction.raw_notes or interaction.summary or "", COMPLIANCE_SYSTEM_PROMPT)
        interaction.compliance_flag = bool(result.get("flag", False))
        interaction.compliance_notes = result.get("notes", "")
        db.commit()
        return {
            "interaction_id": interaction.id,
            "compliance_flag": interaction.compliance_flag,
            "compliance_notes": interaction.compliance_notes,
        }

    return StructuredTool.from_function(
        func=_run,
        name="check_compliance",
        description="Runs the LLM over an interaction's notes to flag potential pharma "
                     "compliance issues — off-label claims, kickback language, "
                     "excessive gifting — before the record is finalized.",
        args_schema=CheckComplianceArgs,
    )


def build_all_tools(db: Session) -> list:
    return [
        make_log_interaction(db),
        make_edit_interaction(db),
        make_get_hcp_profile(db),
        make_schedule_followup(db),
        make_check_compliance(db),
    ]
