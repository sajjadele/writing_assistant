"""Core schemas and contract definitions for Single-Inference AI Engine (ADR-04)."""

from typing import Literal, List, Optional, Dict, Any
from pydantic import BaseModel, Field


ChangeCategory = Literal[
    "grammar",
    "word_choice",
    "phrasing_idiom",
    "bracket_translation",
]


class ChangeItem(BaseModel):
    """Granular linguistic modification for pedagogical feedback."""
    original: str = Field(..., description="The original word, phrase, or bracketed Persian placeholder")
    replacement: str = Field(..., description="The replacement word or phrase in English")
    category: ChangeCategory = Field(..., description="Category of linguistic modification")
    explanation_fa: str = Field(..., description="Brief pedagogical micro-explanation in Persian")


class SingleInferenceResponse(BaseModel):
    """Structured response contract from LLM in a single inference turn."""
    is_correct: bool = Field(
        ...,
        description="True if original text was already grammatically and idiomatically acceptable"
    )
    interpreted_meaning_fa: str = Field(
        ...,
        description="Persian semantic checkpoint summarizing detected user intent to prevent drift"
    )
    corrected_text: str = Field(
        ...,
        description="Proposed natural, fluent English expression preserving original technical identifiers"
    )
    changes: List[ChangeItem] = Field(
        default_factory=list,
        description="Granular breakdown of modifications made to the text"
    )


class IPCRequest(BaseModel):
    """Incoming IPC request payload from GNOME Extension."""
    action: Literal["correct", "log_feedback"]
    text: Optional[str] = None
    preferred_backend: str = "auto"
    event_id: Optional[int] = None
    accepted: Optional[bool] = None


class IPCError(BaseModel):
    """Structured error payload for IPC communication."""
    code: str
    message: str
    is_transient: bool = False


class IPCResponse(BaseModel):
    """Outgoing IPC response payload to GNOME Extension."""
    status: Literal["success", "error"]
    data: Optional[SingleInferenceResponse] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[IPCError] = None
