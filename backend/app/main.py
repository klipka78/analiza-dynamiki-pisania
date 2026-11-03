import csv
import io
import json
import secrets
import zipfile
from datetime import datetime

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db, init_db
from .identify_service import (
    drift_report,
    feature_matrix_rows,
    identify_events,
    identify_status,
    invalidate_cache,
    leave_one_session_out_report,
    protocol_status,
    verify_events,
)
from .kd_features import FEATURE_NAMES
from .models import EventRecord, SessionRecord
from .schemas import (
    IdentifyRequest,
    IdentifyResult,
    IdentifyStatus,
    SessionCreate,
    SessionCreated,
    SessionSummary,
    TaskTexts,
    VerifyRequest,
    VerifyResult,
)
from .tasks import TASK_TEXTS

settings = get_settings()

app = FastAPI(title="Keystroke Dynamics Collector", version="1.1.0")

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
        "protocol": {
            "min_sessions_per_user": settings.min_sessions_per_user,
            "min_events": settings.min_events,
            "min_duration_ms": settings.min_duration_ms,
            "confidence_threshold": settings.confidence_threshold,
        },
    }


@app.get("/api/tasks", response_model=TaskTexts)
def list_tasks() -> TaskTexts:
    return TaskTexts(tasks=TASK_TEXTS)


@app.get("/api/protocol")
def get_protocol(
    participantId: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    return protocol_status(db, participantId)


@app.post("/api/sessions", response_model=SessionCreated)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)) -> SessionCreated:
    pid = payload.participantId.strip()
    tid = payload.taskId.strip().upper()
    if not pid:
        raise HTTPException(status_code=400, detail="participantId required")
    if tid not in TASK_TEXTS and not payload.referenceText.strip():
        raise HTTPException(status_code=400, detail="Unknown taskId")
    if len(payload.events) < settings.min_events:
        raise HTTPException(
            status_code=400,
            detail=f"Za mało zdarzeń (min. {settings.min_events}).",
        )

    duration = payload.durationMs
    if duration <= 0 and payload.events:
        duration = max(0.0, float(payload.events[-1].t) - float(payload.events[0].t))
    if duration < settings.min_duration_ms:
        raise HTTPException(
            status_code=400,
            detail=f"Sesja zbyt krótka (min. {settings.min_duration_ms/1000:.0f} s pisania).",
        )

    reference = payload.referenceText.strip() or TASK_TEXTS.get(tid, "")
    uid = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + secrets.token_hex(4)
    env = (payload.environment or "web").strip().lower()
    if env not in ("web", "word"):
        env = "web"

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
        environment=env,
        keyboard_type=(payload.keyboardType or "")[:32],
        dominant_hand=(payload.dominantHand or "")[:16],
        fatigue=max(0, min(5, int(payload.fatigue or 0))),
        duration_ms=float(duration),
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
    invalidate_cache()
    return SessionCreated(
        id=rec.id,
        session_uid=rec.session_uid,
        event_count=rec.event_count,
        protocol=protocol_status(db, pid).get("participant"),
    )


@app.get("/api/identify/status", response_model=IdentifyStatus)
def get_identify_status(db: Session = Depends(get_db)) -> IdentifyStatus:
    return IdentifyStatus(**identify_status(db))


@app.post("/api/identify", response_model=IdentifyResult)
def post_identify(payload: IdentifyRequest, db: Session = Depends(get_db)) -> IdentifyResult:
    try:
        raw = [e.model_dump() for e in payload.events]
        return IdentifyResult(**identify_events(db, raw))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/verify", response_model=VerifyResult)
def post_verify(payload: VerifyRequest, db: Session = Depends(get_db)) -> VerifyResult:
    try:
        raw = [e.model_dump() for e in payload.events]
        return VerifyResult(**verify_events(db, payload.claimedParticipantId, raw))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


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
            environment=r.environment or "web",
            keyboard_type=r.keyboard_type or "",
            dominant_hand=r.dominant_hand or "",
            fatigue=r.fatigue or 0,
            duration_ms=r.duration_ms or 0,
        )
        for r in rows
    ]


@app.get("/api/admin/model-report")
def model_report(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict:
    try:
        return leave_one_session_out_report(db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/admin/drift")
def admin_drift(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict:
    return drift_report(db)


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

    buf.write("\n# meta\n")
    meta_writer = csv.writer(buf)
    meta_writer.writerow(["field", "value"])
    for field, value in [
        ("session_uid", rec.session_uid),
        ("participant_id", rec.participant_id),
        ("task_id", rec.task_id),
        ("created_at", rec.created_at.isoformat()),
        ("event_count", rec.event_count),
        ("environment", rec.environment),
        ("keyboard_type", rec.keyboard_type),
        ("dominant_hand", rec.dominant_hand),
        ("fatigue", rec.fatigue),
        ("duration_ms", rec.duration_ms),
        ("keyboard_layout", rec.keyboard_layout),
        ("language", rec.language),
        ("user_agent", rec.user_agent),
        ("reference_text", rec.reference_text.replace("\n", "\\n")),
        ("typed_text", rec.typed_text.replace("\n", "\\n")),
    ]:
        meta_writer.writerow([field, value])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{rec.session_uid}_events.csv"'},
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
            "environment",
            "keyboard_type",
            "dominant_hand",
            "fatigue",
            "duration_ms",
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
                    rec.environment,
                    rec.keyboard_type,
                    rec.dominant_hand,
                    rec.fatigue,
                    rec.duration_ms,
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


@app.get("/api/export/ml.zip")
def export_ml_zip(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> Response:
    # all_events
    events_buf = io.StringIO()
    w = csv.writer(events_buf)
    w.writerow(
        [
            "session_uid",
            "participant_id",
            "task_id",
            "environment",
            "keyboard_type",
            "dominant_hand",
            "fatigue",
            "duration_ms",
            "created_at",
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
            w.writerow(
                [
                    rec.session_uid,
                    rec.participant_id,
                    rec.task_id,
                    rec.environment,
                    rec.keyboard_type,
                    rec.dominant_hand,
                    rec.fatigue,
                    rec.duration_ms,
                    rec.created_at.isoformat() if rec.created_at else "",
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

    # features
    feat_rows = feature_matrix_rows(db)
    feat_buf = io.StringIO()
    fw = csv.writer(feat_buf)
    feat_header = ["session_uid", "participant_id", "environment", "created_at", *FEATURE_NAMES]
    fw.writerow(feat_header)
    for row in feat_rows:
        fw.writerow([row.get(h, "") for h in feat_header])

    # meta
    meta = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "n_sessions": len(sessions),
        "n_feature_rows": len(feat_rows),
        "feature_names": FEATURE_NAMES,
        "protocol": {
            "min_sessions_per_user": settings.min_sessions_per_user,
            "min_events": settings.min_events,
            "min_duration_ms": settings.min_duration_ms,
            "confidence_threshold": settings.confidence_threshold,
        },
        "environments": ["web", "word"],
        "note": "ZIP gotowy pod ML (scikit-learn / analysis/recognize_user.py).",
    }

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("all_events.csv", events_buf.getvalue())
        zf.writestr("session_features.csv", feat_buf.getvalue())
        zf.writestr("metadata.json", json.dumps(meta, ensure_ascii=False, indent=2))
    mem.seek(0)

    return Response(
        content=mem.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="pismo_ml_export.zip"'},
    )
