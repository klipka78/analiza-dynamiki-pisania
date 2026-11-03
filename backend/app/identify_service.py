"""Trening i identyfikacja uczestnika na podstawie zapisanych sesji."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sqlalchemy.orm import Session, joinedload

from .kd_features import FEATURE_NAMES, events_from_records, session_feature_vector
from .models import SessionRecord

MIN_SESSIONS_PER_USER = 2
MIN_USERS = 2
MIN_EVENTS = 20


@dataclass
class ModelBundle:
    pipeline: Pipeline
    encoder: LabelEncoder
    n_sessions: int
    n_users: int
    users: list[str]
    sessions_per_user: dict[str, int]


_lock = Lock()
_cache: ModelBundle | None = None
_cache_key: tuple[int, int] | None = None


def _corpus(db: Session) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    rows = (
        db.query(SessionRecord)
        .options(joinedload(SessionRecord.events))
        .order_by(SessionRecord.id.asc())
        .all()
    )
    by_user: dict[str, list[list[float]]] = {}
    for rec in rows:
        if not rec.events or len(rec.events) < MIN_EVENTS:
            continue
        pid = (rec.participant_id or "").strip()
        if not pid:
            continue
        vec = session_feature_vector(events_from_records(list(rec.events)))
        by_user.setdefault(pid, []).append(vec)

    # tylko użytkownicy z ≥ MIN_SESSIONS_PER_USER
    X_list: list[list[float]] = []
    y_list: list[str] = []
    counts: dict[str, int] = {}
    for pid, vectors in by_user.items():
        if len(vectors) < MIN_SESSIONS_PER_USER:
            continue
        counts[pid] = len(vectors)
        for v in vectors:
            X_list.append(v)
            y_list.append(pid)

    if not X_list:
        return np.empty((0, len(FEATURE_NAMES))), np.array([]), {}
    return np.asarray(X_list, dtype=np.float64), np.asarray(y_list), counts


def build_model(db: Session, force: bool = False) -> ModelBundle:
    global _cache, _cache_key

    total_sessions = db.query(SessionRecord).count()
    # prosty klucz invalidacji
    key = (total_sessions, db.query(SessionRecord).order_by(SessionRecord.id.desc()).first().id if total_sessions else 0)

    with _lock:
        if not force and _cache is not None and _cache_key == key:
            return _cache

        X, y, counts = _corpus(db)
        n_users = len(counts)
        if n_users < MIN_USERS or len(X) < MIN_USERS * MIN_SESSIONS_PER_USER:
            raise ValueError(
                f"Za mało danych do identyfikacji. Potrzeba ≥{MIN_USERS} uczestników "
                f"z co najmniej {MIN_SESSIONS_PER_USER} sesjami każdy "
                f"(obecnie kwalifikujących się: {n_users}, sesji treningowych: {len(X)})."
            )

        enc = LabelEncoder()
        y_enc = enc.fit_transform(y)

        # RF gdy jest trochę danych; k-NN też działa przy małych zbiorach
        if len(X) >= 12 and n_users >= 3:
            clf = RandomForestClassifier(
                n_estimators=200,
                random_state=42,
                class_weight="balanced",
                n_jobs=1,
            )
            pipe = Pipeline([("clf", clf)])
        else:
            clf = KNeighborsClassifier(n_neighbors=min(3, len(X) - 1), weights="distance", metric="manhattan")
            pipe = Pipeline([("scaler", StandardScaler()), ("clf", clf)])

        pipe.fit(X, y_enc)
        bundle = ModelBundle(
            pipeline=pipe,
            encoder=enc,
            n_sessions=int(len(X)),
            n_users=n_users,
            users=sorted(counts.keys()),
            sessions_per_user=counts,
        )
        _cache = bundle
        _cache_key = key
        return bundle


def identify_status(db: Session) -> dict:
    try:
        bundle = build_model(db, force=False)
        return {
            "ready": True,
            "n_users": bundle.n_users,
            "n_sessions": bundle.n_sessions,
            "users": bundle.users,
            "sessions_per_user": bundle.sessions_per_user,
            "min_sessions_per_user": MIN_SESSIONS_PER_USER,
            "message": "Model gotowy do identyfikacji.",
        }
    except ValueError as e:
        # policz surowe statystyki dla UI
        rows = db.query(SessionRecord).all()
        raw: dict[str, int] = {}
        for r in rows:
            pid = (r.participant_id or "").strip() or "?"
            raw[pid] = raw.get(pid, 0) + 1
        return {
            "ready": False,
            "n_users": len([u for u, c in raw.items() if c >= MIN_SESSIONS_PER_USER]),
            "n_sessions": sum(raw.values()),
            "users": sorted(raw.keys()),
            "sessions_per_user": raw,
            "min_sessions_per_user": MIN_SESSIONS_PER_USER,
            "message": str(e),
        }


def identify_events(db: Session, raw_events: list[dict], top_k: int = 5) -> dict:
    if len(raw_events) < MIN_EVENTS:
        raise ValueError(f"Za mało zdarzeń w próbce (min. {MIN_EVENTS}). Napisz dłuższy fragment.")

    bundle = build_model(db, force=False)
    events = events_from_records(raw_events)
    vec = np.asarray([session_feature_vector(events)], dtype=np.float64)

    pipe = bundle.pipeline
    pred_enc = int(pipe.predict(vec)[0])
    pred_id = str(bundle.encoder.inverse_transform([pred_enc])[0])

    ranking: list[dict] = []
    proba = None
    if hasattr(pipe, "predict_proba"):
        try:
            proba = pipe.predict_proba(vec)[0]
        except Exception:
            proba = None

    if proba is not None:
        order = np.argsort(proba)[::-1][:top_k]
        for idx in order:
            ranking.append(
                {
                    "participant_id": str(bundle.encoder.inverse_transform([int(idx)])[0]),
                    "score": float(proba[idx]),
                }
            )
    else:
        ranking.append({"participant_id": pred_id, "score": 1.0})

    return {
        "predicted_participant_id": pred_id,
        "ranking": ranking,
        "n_events": len(events),
        "model_users": bundle.n_users,
        "model_sessions": bundle.n_sessions,
    }


def invalidate_cache() -> None:
    global _cache, _cache_key
    with _lock:
        _cache = None
        _cache_key = None
