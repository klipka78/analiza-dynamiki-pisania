from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    participant_id: Mapped[str] = mapped_column(String(64), index=True)
    task_id: Mapped[str] = mapped_column(String(32), index=True)
    reference_text: Mapped[str] = mapped_column(Text)
    typed_text: Mapped[str] = mapped_column(Text)
    user_agent: Mapped[str] = mapped_column(Text, default="")
    keyboard_layout: Mapped[str] = mapped_column(String(64), default="")
    language: Mapped[str] = mapped_column(String(32), default="")
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Warunki sesji / protokół
    environment: Mapped[str] = mapped_column(String(32), default="web")  # web | word
    keyboard_type: Mapped[str] = mapped_column(String(32), default="")  # laptop | external_usb | other
    dominant_hand: Mapped[str] = mapped_column(String(16), default="")  # left | right | both
    fatigue: Mapped[int] = mapped_column(Integer, default=0)  # 1–5, 0 = nie podano
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)

    events: Mapped[list["EventRecord"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="EventRecord.seq",
    )


class EventRecord(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    elapsed_ms: Mapped[str] = mapped_column(String(32))
    event_type: Mapped[str] = mapped_column(String(8))
    code: Mapped[str] = mapped_column(String(64), default="")
    key: Mapped[str] = mapped_column(String(64), default="")
    key_code: Mapped[int] = mapped_column(Integer, default=0)
    shift: Mapped[int] = mapped_column(Integer, default=0)
    ctrl: Mapped[int] = mapped_column(Integer, default=0)
    alt: Mapped[int] = mapped_column(Integer, default=0)

    session: Mapped["SessionRecord"] = relationship(back_populates="events")
