from datetime import datetime

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


class SessionCreated(BaseModel):
    id: int
    session_uid: str
    event_count: int


class TaskTexts(BaseModel):
    tasks: dict[str, str]
