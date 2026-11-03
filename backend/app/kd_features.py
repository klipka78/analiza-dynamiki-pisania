"""Cechy keystroke dynamics (hold, digraph, WPM, Backspace) — wersja serwerowa."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

COMMON_KEYS = [
    "KeyA",
    "KeyE",
    "KeyI",
    "KeyO",
    "KeyN",
    "KeyS",
    "KeyT",
    "Space",
    "Backspace",
]

COMMON_DIGRAPHS = [
    "KeyT>KeyE",
    "KeyE>KeyN",
    "KeyA>KeyN",
    "KeyN>KeyI",
    "KeyS>KeyI",
    "KeyO>KeyW",
    "KeyA>KeyL",
    "Space>KeyA",
    "KeyE>Space",
    "KeyY>Space",
]

FEATURE_NAMES: list[str] = (
    [
        "hold_mean",
        "hold_std",
        "hold_median",
        "flight_mean",
        "flight_std",
        "flight_median",
    ]
    + [f"hold_{k}" for k in COMMON_KEYS]
    + [f"dig_{d}" for d in COMMON_DIGRAPHS]
    + ["wpm", "backspace_pct", "n_events", "n_holds", "n_digraphs"]
)


def _norm_code(code: str, key: str, key_code: int) -> str:
    code = (code or "").strip()
    key = key or ""
    if code:
        return code
    if key == " ":
        return "Space"
    if key == "Backspace":
        return "Backspace"
    if len(key) == 1 and key.isalpha():
        return f"Key{key.upper()}"
    if key:
        return key
    if key_code == 32:
        return "Space"
    if key_code == 8:
        return "Backspace"
    if 65 <= key_code <= 90:
        return f"Key{chr(key_code)}"
    return f"VK_{key_code}"


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5


def _median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return 0.5 * (s[mid - 1] + s[mid])


def events_from_records(rows: list[Any]) -> list[dict[str, Any]]:
    """EventRecord ORM / dict → lista znormalizowana."""
    out: list[dict[str, Any]] = []
    for r in rows:
        if hasattr(r, "elapsed_ms"):
            et = str(r.event_type).lower()
            try:
                t = float(r.elapsed_ms)
            except (TypeError, ValueError):
                continue
            code = getattr(r, "code", "") or ""
            key = getattr(r, "key", "") or ""
            kc = int(getattr(r, "key_code", 0) or 0)
            seq = int(getattr(r, "seq", 0) or 0)
        else:
            et = str(r.get("type") or r.get("event_type") or "").lower()
            try:
                t = float(r.get("t") if r.get("t") is not None else r.get("elapsed_ms"))
            except (TypeError, ValueError):
                continue
            code = r.get("code") or ""
            key = r.get("key") or ""
            kc = int(r.get("keyCode") or r.get("key_code") or 0)
            seq = int(r.get("seq") or 0)
        if et not in ("down", "up"):
            continue
        out.append(
            {
                "seq": seq,
                "elapsed_ms": t,
                "event_type": et,
                "key_id": _norm_code(code, key, kc),
            }
        )
    out.sort(key=lambda e: (e["seq"], e["elapsed_ms"]))
    return out


def session_feature_vector(events: list[dict[str, Any]]) -> list[float]:
    stacks: dict[str, list[float]] = defaultdict(list)
    holds: list[tuple[str, float]] = []
    for e in events:
        kid = e["key_id"]
        t = e["elapsed_ms"]
        if e["event_type"] == "down":
            stacks[kid].append(t)
        elif e["event_type"] == "up" and stacks[kid]:
            t0 = stacks[kid].pop()
            ht = t - t0
            if 5.0 <= ht <= 2000.0:
                holds.append((kid, ht))

    downs = [e for e in events if e["event_type"] == "down"]
    digs: list[tuple[str, float]] = []
    prev_key = None
    prev_t = None
    for e in downs:
        kid = e["key_id"]
        t = e["elapsed_ms"]
        if prev_key is not None and prev_t is not None:
            lat = t - prev_t
            if 5.0 <= lat <= 3000.0:
                digs.append((f"{prev_key}>{kid}", lat))
        prev_key, prev_t = kid, t

    hold_by: dict[str, list[float]] = defaultdict(list)
    for k, v in holds:
        hold_by[k].append(v)
    dig_by: dict[str, list[float]] = defaultdict(list)
    for k, v in digs:
        dig_by[k].append(v)

    all_holds = [v for _, v in holds]
    all_digs = [v for _, v in digs]
    hold_mean = _mean(all_holds)
    flight_mean = _mean(all_digs)

    feats: dict[str, float] = {
        "hold_mean": hold_mean,
        "hold_std": _std(all_holds),
        "hold_median": _median(all_holds),
        "flight_mean": flight_mean,
        "flight_std": _std(all_digs),
        "flight_median": _median(all_digs),
    }
    for k in COMMON_KEYS:
        vals = hold_by.get(k, [])
        feats[f"hold_{k}"] = _mean(vals) if vals else hold_mean
    for d in COMMON_DIGRAPHS:
        vals = dig_by.get(d, [])
        feats[f"dig_{d}"] = _mean(vals) if vals else flight_mean

    if events:
        duration_s = max((events[-1]["elapsed_ms"] - events[0]["elapsed_ms"]) / 1000.0, 1e-6)
    else:
        duration_s = 1e-6
    char_downs = [e for e in downs if e["key_id"] not in ("Shift", "Ctrl", "Alt", "Meta", "CapsLock")]
    n_chars = max(len(char_downs), 1)
    feats["wpm"] = (n_chars / 5.0) / (duration_s / 60.0)
    n_bs = sum(1 for e in downs if e["key_id"] == "Backspace")
    feats["backspace_pct"] = 100.0 * n_bs / n_chars
    feats["n_events"] = float(len(events))
    feats["n_holds"] = float(len(holds))
    feats["n_digraphs"] = float(len(digs))

    return [feats[name] for name in FEATURE_NAMES]
