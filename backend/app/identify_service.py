"""Identyfikacja 1:N, weryfikacja 1:1, LOSO, drift cech."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from threading import Lock

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sqlalchemy.orm import Session, joinedload

from .config import get_settings
from .kd_features import FEATURE_NAMES, events_from_records, session_feature_vector
from .models import SessionRecord

settings = get_settings()


@dataclass
class SessionVec:
    session_uid: str
    participant_id: str
    created_at: datetime
    environment: str
    vector: list[float]


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


def _load_session_vecs(db: Session) -> list[SessionVec]:
    rows = (
        db.query(SessionRecord)
        .options(joinedload(SessionRecord.events))
        .order_by(SessionRecord.id.asc())
        .all()
    )
    out: list[SessionVec] = []
    for rec in rows:
        if not rec.events or len(rec.events) < settings.min_events:
            continue
        # też respektuj duration jeśli zapisana
        if rec.duration_ms and rec.duration_ms < settings.min_duration_ms * 0.5:
            continue
        pid = (rec.participant_id or "").strip()
        if not pid:
            continue
        vec = session_feature_vector(events_from_records(list(rec.events)))
        out.append(
            SessionVec(
                session_uid=rec.session_uid,
                participant_id=pid,
                created_at=rec.created_at or datetime.utcnow(),
                environment=(rec.environment or "web"),
                vector=vec,
            )
        )
    return out


def _eligible_corpus(vecs: list[SessionVec]) -> tuple[list[SessionVec], dict[str, int]]:
    counts: dict[str, int] = defaultdict(int)
    for v in vecs:
        counts[v.participant_id] += 1
    min_s = settings.min_sessions_per_user
    keep = {pid for pid, c in counts.items() if c >= min_s}
    filtered = [v for v in vecs if v.participant_id in keep]
    return filtered, {pid: counts[pid] for pid in sorted(keep)}


def _make_pipeline(n_samples: int, n_users: int) -> Pipeline:
    if n_samples >= 12 and n_users >= 3:
        return Pipeline(
            [
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=200,
                        random_state=42,
                        class_weight="balanced",
                        n_jobs=1,
                    ),
                )
            ]
        )
    k = max(1, min(3, n_samples - 1))
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", KNeighborsClassifier(n_neighbors=k, weights="distance", metric="manhattan")),
        ]
    )


def build_model(db: Session, force: bool = False) -> ModelBundle:
    global _cache, _cache_key

    total_sessions = db.query(SessionRecord).count()
    last = db.query(SessionRecord).order_by(SessionRecord.id.desc()).first()
    key = (total_sessions, last.id if last else 0)

    with _lock:
        if not force and _cache is not None and _cache_key == key:
            return _cache

        vecs, counts = _eligible_corpus(_load_session_vecs(db))
        n_users = len(counts)
        if n_users < settings.min_users_for_model or len(vecs) < settings.min_users_for_model * settings.min_sessions_per_user:
            raise ValueError(
                f"Za mało danych. Potrzeba ≥{settings.min_users_for_model} uczestników "
                f"z co najmniej {settings.min_sessions_per_user} sesjami każdy "
                f"(kwalifikujących się: {n_users}, sesji: {len(vecs)})."
            )

        X = np.asarray([v.vector for v in vecs], dtype=np.float64)
        y = np.asarray([v.participant_id for v in vecs])
        enc = LabelEncoder()
        y_enc = enc.fit_transform(y)
        pipe = _make_pipeline(len(X), n_users)
        pipe.fit(X, y_enc)

        bundle = ModelBundle(
            pipeline=pipe,
            encoder=enc,
            n_sessions=len(vecs),
            n_users=n_users,
            users=sorted(counts.keys()),
            sessions_per_user=counts,
        )
        _cache = bundle
        _cache_key = key
        return bundle


def protocol_status(db: Session, participant_id: str | None = None) -> dict:
    rows = db.query(SessionRecord).all()
    raw: dict[str, int] = defaultdict(int)
    by_task: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        pid = (r.participant_id or "").strip() or "?"
        raw[pid] += 1
        by_task[pid][r.task_id] += 1

    min_s = settings.min_sessions_per_user
    eligible_users = [u for u, c in raw.items() if c >= min_s]
    ready = len(eligible_users) >= settings.min_users_for_model

    me = None
    if participant_id:
        pid = participant_id.strip()
        n = raw.get(pid, 0)
        me = {
            "participant_id": pid,
            "sessions": n,
            "sessions_by_task": dict(by_task.get(pid, {})),
            "remaining": max(0, min_s - n),
            "enrolled": n >= min_s,
            "recommended_task": settings.protocol_task_id,
        }

    return {
        "ready": ready,
        "min_sessions_per_user": min_s,
        "min_users_for_model": settings.min_users_for_model,
        "min_events": settings.min_events,
        "min_duration_ms": settings.min_duration_ms,
        "confidence_threshold": settings.confidence_threshold,
        "protocol_task_id": settings.protocol_task_id,
        "n_users_eligible": len(eligible_users),
        "sessions_per_user": dict(raw),
        "participant": me,
    }


def identify_status(db: Session) -> dict:
    proto = protocol_status(db)
    try:
        bundle = build_model(db, force=False)
        return {
            "ready": True,
            "n_users": bundle.n_users,
            "n_sessions": bundle.n_sessions,
            "users": bundle.users,
            "sessions_per_user": bundle.sessions_per_user,
            "min_sessions_per_user": settings.min_sessions_per_user,
            "min_events": settings.min_events,
            "min_duration_ms": settings.min_duration_ms,
            "confidence_threshold": settings.confidence_threshold,
            "message": "Model gotowy do identyfikacji i weryfikacji.",
            "protocol": proto,
        }
    except ValueError as e:
        return {
            "ready": False,
            "n_users": proto["n_users_eligible"],
            "n_sessions": sum(proto["sessions_per_user"].values()),
            "users": sorted(proto["sessions_per_user"].keys()),
            "sessions_per_user": proto["sessions_per_user"],
            "min_sessions_per_user": settings.min_sessions_per_user,
            "min_events": settings.min_events,
            "min_duration_ms": settings.min_duration_ms,
            "confidence_threshold": settings.confidence_threshold,
            "message": str(e),
            "protocol": proto,
        }


def _score_vector(bundle: ModelBundle, vec: np.ndarray) -> tuple[str, float, list[dict]]:
    pipe = bundle.pipeline
    pred_enc = int(pipe.predict(vec)[0])
    pred_id = str(bundle.encoder.inverse_transform([pred_enc])[0])
    ranking: list[dict] = []
    top_score = 1.0
    try:
        proba = pipe.predict_proba(vec)[0]
        order = np.argsort(proba)[::-1][:5]
        for idx in order:
            ranking.append(
                {
                    "participant_id": str(bundle.encoder.inverse_transform([int(idx)])[0]),
                    "score": float(proba[idx]),
                }
            )
        top_score = float(ranking[0]["score"]) if ranking else 0.0
    except Exception:
        ranking = [{"participant_id": pred_id, "score": 1.0}]
        top_score = 1.0
    return pred_id, top_score, ranking


def _validate_sample(raw_events: list[dict]) -> tuple[list[dict], float]:
    if len(raw_events) < settings.min_events:
        raise ValueError(
            f"Za mało zdarzeń (min. {settings.min_events}). Napisz dłuższy fragment."
        )
    events = events_from_records(raw_events)
    if len(events) < 2:
        raise ValueError("Brak poprawnych zdarzeń down/up.")
    duration = float(events[-1]["elapsed_ms"] - events[0]["elapsed_ms"])
    if duration < settings.min_duration_ms:
        raise ValueError(
            f"Próbka zbyt krótka ({duration/1000:.1f} s). "
            f"Minimum: {settings.min_duration_ms/1000:.0f} s."
        )
    return events, duration


def identify_events(db: Session, raw_events: list[dict]) -> dict:
    events, duration = _validate_sample(raw_events)
    bundle = build_model(db, force=False)
    vec = np.asarray([session_feature_vector(events)], dtype=np.float64)
    pred_id, top_score, ranking = _score_vector(bundle, vec)
    threshold = settings.confidence_threshold
    identified = top_score >= threshold
    return {
        "predicted_participant_id": pred_id if identified else None,
        "identified": identified,
        "confidence": top_score,
        "threshold": threshold,
        "ranking": ranking,
        "n_events": len(events),
        "duration_ms": duration,
        "model_users": bundle.n_users,
        "model_sessions": bundle.n_sessions,
        "message": (
            f"Rozpoznano: {pred_id}"
            if identified
            else f"Niezidentyfikowano (pewność {top_score:.0%} < próg {threshold:.0%})."
        ),
    }


def verify_events(db: Session, claimed_id: str, raw_events: list[dict]) -> dict:
    claimed = claimed_id.strip()
    if not claimed:
        raise ValueError("Podaj claimedParticipantId.")
    events, duration = _validate_sample(raw_events)
    bundle = build_model(db, force=False)
    if claimed not in bundle.users:
        raise ValueError(
            f"Uczestnik {claimed} nie ma wystarczającej liczby sesji enroll "
            f"(≥{settings.min_sessions_per_user})."
        )

    vec = np.asarray([session_feature_vector(events)], dtype=np.float64)
    pred_id, top_score, ranking = _score_vector(bundle, vec)

    # score dla claimed
    claimed_score = 0.0
    for h in ranking:
        if h["participant_id"] == claimed:
            claimed_score = float(h["score"])
            break
    if claimed_score == 0.0:
        # spróbuj predict_proba bezpośrednio
        try:
            proba = bundle.pipeline.predict_proba(vec)[0]
            enc_idx = list(bundle.encoder.classes_).index(claimed) if claimed in bundle.encoder.classes_ else -1
            # encoder.classes_ are original labels for LabelEncoder
            classes = list(bundle.encoder.classes_)
            if claimed in classes:
                claimed_score = float(proba[classes.index(claimed)])
        except Exception:
            claimed_score = 1.0 if pred_id == claimed else 0.0

    threshold = settings.confidence_threshold
    accepted = claimed_score >= threshold and pred_id == claimed
    # łagodniejsza weryfikacja: wystarczy score claimed ≥ threshold
    accepted = claimed_score >= threshold

    return {
        "claimed_participant_id": claimed,
        "accepted": accepted,
        "score": claimed_score,
        "threshold": threshold,
        "predicted_participant_id": pred_id,
        "ranking": ranking,
        "n_events": len(events),
        "duration_ms": duration,
        "message": (
            f"TAK — dynamika zgodna z {claimed} (score {claimed_score:.0%})."
            if accepted
            else f"NIE — brak potwierdzenia dla {claimed} (score {claimed_score:.0%} < {threshold:.0%})."
        ),
    }


def leave_one_session_out_report(db: Session) -> dict:
    vecs, counts = _eligible_corpus(_load_session_vecs(db))
    if len(counts) < settings.min_users_for_model or len(vecs) < 4:
        raise ValueError("Za mało danych do raportu LOSO.")

    y_true: list[str] = []
    y_pred: list[str] = []
    details: list[dict] = []

    for i, test in enumerate(vecs):
        train = [v for j, v in enumerate(vecs) if j != i]
        # po usunięciu jednej sesji użytkownik musi mieć ≥1 próbkę
        train_counts: dict[str, int] = defaultdict(int)
        for v in train:
            train_counts[v.participant_id] += 1
        if train_counts.get(test.participant_id, 0) < 1:
            continue
        # tylko userzy obecni w train
        train = [v for v in train if train_counts[v.participant_id] >= 1]
        users_in_train = {v.participant_id for v in train}
        if test.participant_id not in users_in_train or len(users_in_train) < 2:
            continue

        X_tr = np.asarray([v.vector for v in train], dtype=np.float64)
        y_tr = np.asarray([v.participant_id for v in train])
        enc = LabelEncoder()
        y_enc = enc.fit_transform(y_tr)
        pipe = _make_pipeline(len(X_tr), len(enc.classes_))
        pipe.fit(X_tr, y_enc)
        X_te = np.asarray([test.vector], dtype=np.float64)
        pred = str(enc.inverse_transform([int(pipe.predict(X_te)[0])])[0])
        y_true.append(test.participant_id)
        y_pred.append(pred)
        details.append(
            {
                "session_uid": test.session_uid,
                "true": test.participant_id,
                "pred": pred,
                "ok": pred == test.participant_id,
            }
        )

    if len(y_true) < 2:
        raise ValueError("Za mało foldów LOSO (potrzeba więcej sesji).")

    labels = sorted(set(y_true) | set(y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()
    return {
        "n_folds": len(y_true),
        "n_users": len(counts),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "labels": labels,
        "confusion_matrix": cm,
        "sessions_per_user": counts,
        "details": details,
    }


def drift_report(db: Session) -> dict:
    """Porównanie wczesnych vs późnych sesji (proxy dzień 1 vs później)."""
    vecs, counts = _eligible_corpus(_load_session_vecs(db))
    # hold_mean idx, flight_mean, wpm
    idx_hold = FEATURE_NAMES.index("hold_mean")
    idx_flight = FEATURE_NAMES.index("flight_mean")
    idx_wpm = FEATURE_NAMES.index("wpm")

    by_user: dict[str, list[SessionVec]] = defaultdict(list)
    for v in vecs:
        by_user[v.participant_id].append(v)

    users_out: list[dict] = []
    for pid, items in sorted(by_user.items()):
        items = sorted(items, key=lambda x: x.created_at)
        if len(items) < 2:
            continue
        mid = max(1, len(items) // 2)
        early, late = items[:mid], items[mid:]

        def avg(part: list[SessionVec], i: int) -> float:
            return float(np.mean([p.vector[i] for p in part]))

        users_out.append(
            {
                "participant_id": pid,
                "n_early": len(early),
                "n_late": len(late),
                "early_date": early[0].created_at.isoformat(),
                "late_date": late[-1].created_at.isoformat(),
                "hold_mean_early": avg(early, idx_hold),
                "hold_mean_late": avg(late, idx_hold),
                "flight_mean_early": avg(early, idx_flight),
                "flight_mean_late": avg(late, idx_flight),
                "wpm_early": avg(early, idx_wpm),
                "wpm_late": avg(late, idx_wpm),
                "hold_drift_pct": _pct(avg(early, idx_hold), avg(late, idx_hold)),
                "flight_drift_pct": _pct(avg(early, idx_flight), avg(late, idx_flight)),
                "wpm_drift_pct": _pct(avg(early, idx_wpm), avg(late, idx_wpm)),
                "environments": sorted({p.environment for p in items}),
            }
        )

    env_counts: dict[str, int] = defaultdict(int)
    for v in vecs:
        env_counts[v.environment] += 1

    return {
        "users": users_out,
        "environment_counts": dict(env_counts),
        "note": "Early/late = pierwsza vs druga połowa sesji chronologicznie (proxy stabilności w czasie).",
    }


def _pct(a: float, b: float) -> float:
    if abs(a) < 1e-9:
        return 0.0
    return 100.0 * (b - a) / a


def feature_matrix_rows(db: Session) -> list[dict]:
    vecs, _ = _eligible_corpus(_load_session_vecs(db))
    # do ZIP: wszystkie kwalifikujące się + ewentualnie pozostałe z min_events
    all_vecs = _load_session_vecs(db)
    rows = []
    for v in all_vecs:
        row = {
            "session_uid": v.session_uid,
            "participant_id": v.participant_id,
            "environment": v.environment,
            "created_at": v.created_at.isoformat(),
        }
        for name, val in zip(FEATURE_NAMES, v.vector):
            row[name] = val
        rows.append(row)
    return rows


def invalidate_cache() -> None:
    global _cache, _cache_key
    with _lock:
        _cache = None
        _cache_key = None
