# backend/models.py

from pydantic import BaseModel, Field, ConfigDict # Import ConfigDict for Pydantic V2 config
from typing import Optional, List
from datetime import date, time, datetime
from sqlalchemy import Column, Integer, String, Date, Time, Text, Enum as SQLEnum, DateTime, func
from backend.database import Base # Import Base from database.py
import enum

# --- Pydantic Models for API Validation ---

class SentimentEnum(str, enum.Enum):
    """ Enum for HCP Sentiment """
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"

class InteractionBase(BaseModel):
    """ Base Pydantic model for interaction data """
    hcp_name: Optional[str] = Field(None, description="Name of the Healthcare Professional")
    interaction_type: Optional[str] = Field(None, description="Type of interaction (e.g., Meeting, Call)")
    interaction_date: Optional[date] = Field(None, description="Date of interaction")
    interaction_time: Optional[time] = Field(None, description="Time of interaction")
    attendees: Optional[List[str]] = Field(None, description="List of attendee names")
    topics_discussed: Optional[str] = Field(None, description="Key discussion points")
    materials_shared: Optional[List[str]] = Field(None, description="Materials shared or Samples Distributed")
    samples_distributed: Optional[List[str]] = Field(None, description="Samples distributed")
    hcp_sentiment: Optional[SentimentEnum] = Field(None, description="Observed or inferred HCP sentiment")
    outcomes: Optional[str] = Field(None, description="Key outcomes or agreements")
    follow_up_actions: Optional[str] = Field(None, description="Next steps or tasks")

    # Pydantic V2 configuration using model_config
    model_config = ConfigDict(
        from_attributes=True # Replaces orm_mode = True
    )


class InteractionCreate(InteractionBase):
    """ Pydantic model for creating a new interaction (inherits validation) """
    # Add any fields required only on creation, if any
    pass

class Interaction(InteractionBase):
    """ Pydantic model for representing an interaction (e.g., in API responses) """
    id: int
    created_at: datetime
    updated_at: datetime

    # Inherits model_config from InteractionBase, including from_attributes=True
    # If InteractionBase didn't have it, you would add model_config here:
    # model_config = ConfigDict(
    #     from_attributes=True
    # )


class ParseRequest(BaseModel):
    """ Pydantic model for the text parsing request """
    text: str = Field(..., description="Free-form text describing the interaction")

class ParseResponse(InteractionBase):
    """
    Pydantic model for the response from the parsing endpoint.
    Includes extracted fields, potentially with nulls if not found.
    """
    # This model inherits all fields and model_config from InteractionBase
    pass

# --- SQLAlchemy Model for Database Table ---

class InteractionDB(Base):
    """ SQLAlchemy model representing the 'interactions' table """
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_name = Column(String, index=True)
    interaction_type = Column(String)
    interaction_date = Column(Date)
    interaction_time = Column(Time)
    # Use Text for potentially long strings, or JSON for structured lists if DB supports it well
    attendees = Column(Text) # Store as comma-separated string or JSON string
    topics_discussed = Column(Text)
    materials_shared = Column(Text) # Store as comma-separated string or JSON string
    samples_distributed = Column(Text) # Store as comma-separated string or JSON string
    hcp_sentiment = Column(SQLEnum(SentimentEnum, name="sentiment_enum"), default=SentimentEnum.NEUTRAL)
    outcomes = Column(Text)
    follow_up_actions = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Helper methods to handle list-like fields stored as text
    def set_attendees(self, attendees_list: List[str]):
        self.attendees = ",".join(attendees_list) if attendees_list else None

    def get_attendees(self) -> List[str]:
        return self.attendees.split(',') if self.attendees else []

    def set_materials_shared(self, materials_list: List[str]):
        self.materials_shared = ",".join(materials_list) if materials_list else None

    def get_materials_shared(self) -> List[str]:
        return self.materials_shared.split(',') if self.materials_shared else []

    def set_samples_distributed(self, samples_list: List[str]):
        self.samples_distributed = ",".join(samples_list) if samples_list else None

    def get_samples_distributed(self) -> List[str]:
        return self.samples_distributed.split(',') if self.samples_distributed else []
