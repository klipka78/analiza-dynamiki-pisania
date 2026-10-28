import csv
import io
import secrets
from datetime import datetime

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db, init_db
from .models import EventRecord, SessionRecord
from .schemas import SessionCreate, SessionCreated, SessionSummary, TaskTexts
from .tasks import TASK_TEXTS

settings = get_settings()

app = FastAPI(title="Keystroke Dynamics Collector", version="1.0.0")

origins = {
    settings.public_url.rstrip("/"),
    f"https://{settings.domain}",
    f"http://{settings.domain}",
    "http://localhost",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "domain": settings.domain,
        "public_url": settings.public_url,
        "env": settings.app_env,
    }


@app.get("/api/tasks", response_model=TaskTexts)
def list_tasks() -> TaskTexts:
    return TaskTexts(tasks=TASK_TEXTS)


@app.post("/api/sessions", response_model=SessionCreated)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)) -> SessionCreated:
    pid = payload.participantId.strip()
    tid = payload.taskId.strip().upper()
    if not pid:
        raise HTTPException(status_code=400, detail="participantId required")
    if tid not in TASK_TEXTS and not payload.referenceText.strip():
        raise HTTPException(status_code=400, detail="Unknown taskId")

    reference = payload.referenceText.strip() or TASK_TEXTS.get(tid, "")
    uid = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + secrets.token_hex(4)

    rec = SessionRecord(
        session_uid=uid,
        participant_id=pid,
        task_id=tid,
        reference_text=reference,
        typed_text=payload.typedText,
        user_agent=payload.userAgent[:1000],
        keyboard_layout=payload.keyboardLayout[:64],
        language=payload.language[:32],
        event_count=len(payload.events),
    )
    db.add(rec)
    db.flush()

    for i, ev in enumerate(payload.events, start=1):
        db.add(
            EventRecord(
                session_id=rec.id,
                seq=i,
                elapsed_ms=f"{ev.t:.3f}",
                event_type=ev.type,
                code=ev.code[:64],
                key=ev.key[:64],
                key_code=int(ev.keyCode or 0),
                shift=1 if ev.shift else 0,
                ctrl=1 if ev.ctrl else 0,
                alt=1 if ev.alt else 0,
            )
        )

    db.commit()
    db.refresh(rec)
    return SessionCreated(id=rec.id, session_uid=rec.session_uid, event_count=rec.event_count)


@app.get("/api/sessions", response_model=list[SessionSummary])
def list_sessions(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> list[SessionSummary]:
    rows = db.query(SessionRecord).order_by(SessionRecord.id.desc()).limit(500).all()
    return [
        SessionSummary(
            id=r.id,
            session_uid=r.session_uid,
            participant_id=r.participant_id,
            task_id=r.task_id,
            event_count=r.event_count,
            created_at=r.created_at,
            typed_len=len(r.typed_text or ""),
            reference_len=len(r.reference_text or ""),
        )
        for r in rows
    ]


@app.get("/api/sessions/{session_uid}/export.csv")
def export_session_csv(
    session_uid: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> Response:
    rec = db.query(SessionRecord).filter(SessionRecord.session_uid == session_uid).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["seq", "elapsed_ms", "event_type", "code", "key", "key_code", "shift", "ctrl", "alt"])
    for ev in rec.events:
        writer.writerow(
            [ev.seq, ev.elapsed_ms, ev.event_type, ev.code, ev.key, ev.key_code, ev.shift, ev.ctrl, ev.alt]
        )

    # meta as comment footer-like second section
    buf.write("\n# meta\n")
    meta_writer = csv.writer(buf)
    meta_writer.writerow(["field", "value"])
    for field, value in [
        ("session_uid", rec.session_uid),
        ("participant_id", rec.participant_id),
        ("task_id", rec.task_id),
        ("created_at", rec.created_at.isoformat()),
        ("event_count", rec.event_count),
        ("keyboard_layout", rec.keyboard_layout),
        ("language", rec.language),
        ("user_agent", rec.user_agent),
        ("reference_text", rec.reference_text.replace("\n", "\\n")),
        ("typed_text", rec.typed_text.replace("\n", "\\n")),
    ]:
        meta_writer.writerow([field, value])

    filename = f"{rec.session_uid}_events.csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/export/all.csv")
def export_all_csv(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> Response:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "session_uid",
            "participant_id",
            "task_id",
            "seq",
            "elapsed_ms",
            "event_type",
            "code",
            "key",
            "key_code",
            "shift",
            "ctrl",
            "alt",
        ]
    )
    sessions = db.query(SessionRecord).order_by(SessionRecord.id.asc()).all()
    for rec in sessions:
        for ev in rec.events:
            writer.writerow(
                [
                    rec.session_uid,
                    rec.participant_id,
                    rec.task_id,
                    ev.seq,
                    ev.elapsed_ms,
                    ev.event_type,
                    ev.code,
                    ev.key,
                    ev.key_code,
                    ev.shift,
                    ev.ctrl,
                    ev.alt,
                ]
            )

    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="all_events.csv"'},
    )
