import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON, Boolean
)
from sqlalchemy.orm import relationship

from app.database import Base


class InteractionChannel(str, enum.Enum):
    IN_PERSON = "in_person"
    VIRTUAL = "virtual"
    PHONE = "phone"
    EMAIL = "email"
    CONFERENCE = "conference"


class InteractionSentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    specialty = Column(String(255))
    institution = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    preferred_channel = Column(String(50), default="in_person")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), nullable=False)
    rep_name = Column(String(255), default="Field Rep")
    channel = Column(Enum(InteractionChannel), default=InteractionChannel.IN_PERSON)
    raw_notes = Column(Text)  # original free-text / chat transcript
    summary = Column(Text)  # LLM-generated summary
    topics_discussed = Column(JSON)  # list of extracted topics/products
    samples_distributed = Column(JSON)  # list of {product, qty}
    sentiment = Column(Enum(InteractionSentiment), default=InteractionSentiment.NEUTRAL)
    compliance_flag = Column(Boolean, default=False)
    compliance_notes = Column(Text)
    interaction_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(20), default="form")  # "form" or "chat"

    hcp = relationship("HCP", back_populates="interactions")
    followups = relationship("FollowUp", back_populates="interaction", cascade="all, delete-orphan")


class FollowUp(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id"), nullable=False)
    due_date = Column(DateTime)
    task = Column(Text)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    interaction = relationship("Interaction", back_populates="followups")
