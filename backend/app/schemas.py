from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class KeystrokeEventIn(BaseModel):
    t: float = Field(..., description="performance.now() ms from session start")
    type: str = Field(..., pattern="^(down|up)$")
    code: str = ""
    key: str = ""
    keyCode: int = 0
    shift: bool = False
    ctrl: bool = False
    alt: bool = False


class SessionCreate(BaseModel):
    participantId: str = Field(..., min_length=1, max_length=64)
    taskId: str = Field(..., min_length=1, max_length=32)
    referenceText: str
    typedText: str
    keyboardLayout: str = ""
    language: str = ""
    userAgent: str = ""
    environment: str = "web"
    keyboardType: str = ""
    dominantHand: str = ""
    fatigue: int = 0
    durationMs: float = 0
    events: list[KeystrokeEventIn] = Field(default_factory=list)


class SessionSummary(BaseModel):
    id: int
    session_uid: str
    participant_id: str
    task_id: str
    event_count: int
    created_at: datetime
    typed_len: int
    reference_len: int
    environment: str = "web"
    keyboard_type: str = ""
    dominant_hand: str = ""
    fatigue: int = 0
    duration_ms: float = 0


class SessionCreated(BaseModel):
    id: int
    session_uid: str
    event_count: int
    protocol: dict[str, Any] | None = None


class TaskTexts(BaseModel):
    tasks: dict[str, str]


class IdentifyRequest(BaseModel):
    events: list[KeystrokeEventIn] = Field(default_factory=list)
    typedText: str = ""


class VerifyRequest(BaseModel):
    claimedParticipantId: str = Field(..., min_length=1, max_length=64)
    events: list[KeystrokeEventIn] = Field(default_factory=list)
    typedText: str = ""


class IdentifyHit(BaseModel):
    participant_id: str
    score: float


class IdentifyResult(BaseModel):
    predicted_participant_id: str | None
    identified: bool = True
    confidence: float = 0
    threshold: float = 0
    ranking: list[IdentifyHit]
    n_events: int
    duration_ms: float = 0
    model_users: int
    model_sessions: int
    message: str = ""


class VerifyResult(BaseModel):
    claimed_participant_id: str
    accepted: bool
    score: float
    threshold: float
    predicted_participant_id: str
    ranking: list[IdentifyHit]
    n_events: int
    duration_ms: float = 0
    message: str


class IdentifyStatus(BaseModel):
    ready: bool
    n_users: int
    n_sessions: int
    users: list[str]
    sessions_per_user: dict[str, int]
    min_sessions_per_user: int
    min_events: int = 40
    min_duration_ms: float = 15000
    confidence_threshold: float = 0.45
    message: str
    protocol: dict[str, Any] | None = None
