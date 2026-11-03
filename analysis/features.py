"""Ekstrakcja cech keystroke dynamics z eventów systemu pismo."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

# Stały słownik digrafów / klawiszy — wektor cech tej samej długości dla każdej sesji
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


def _norm_code(row: pd.Series) -> str:
    """Ujednolica kod klawisza z eksportu WEB (code/key) i Word (key_name)."""
    code = str(row.get("code") or "").strip()
    key = str(row.get("key") or "").strip()
    key_name = str(row.get("key_name") or "").strip()

    if code and code not in ("nan", "None"):
        return code
    if key_name and key_name not in ("nan", "None"):
        mapping = {
            "Space": "Space",
            "Backspace": "Backspace",
            "Enter": "Enter",
            "Shift": "Shift",
            "Tab": "Tab",
        }
        if key_name in mapping:
            return mapping[key_name]
        if len(key_name) == 1 and key_name.isalpha():
            return f"Key{key_name.upper()}"
        return key_name
    if key and key not in ("nan", "None"):
        if key == " ":
            return "Space"
        if key == "Backspace":
            return "Backspace"
        if len(key) == 1 and key.isalpha():
            return f"Key{key.upper()}"
        return key
    kc = row.get("key_code")
    try:
        kc_i = int(kc)
    except (TypeError, ValueError):
        return "Unknown"
    if kc_i == 32:
        return "Space"
    if kc_i == 8:
        return "Backspace"
    if 65 <= kc_i <= 90:
        return f"Key{chr(kc_i)}"
    return f"VK_{kc_i}"


def normalize_events(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["elapsed_ms"] = pd.to_numeric(out["elapsed_ms"], errors="coerce")
    out = out.dropna(subset=["elapsed_ms"])
    out["event_type"] = out["event_type"].astype(str).str.lower().str.strip()
    out["key_id"] = out.apply(_norm_code, axis=1)
    return out.sort_values(["session_uid", "seq"] if "seq" in out.columns else ["session_uid", "elapsed_ms"])


def hold_times(events: pd.DataFrame) -> list[tuple[str, float]]:
    """Pary (key_id, hold_ms) z dopasowania down→up tego samego klawisza (stack)."""
    stacks: dict[str, list[float]] = defaultdict(list)
    holds: list[tuple[str, float]] = []
    for _, row in events.iterrows():
        kid = row["key_id"]
        t = float(row["elapsed_ms"])
        et = row["event_type"]
        if et == "down":
            stacks[kid].append(t)
        elif et == "up" and stacks[kid]:
            t0 = stacks[kid].pop()
            ht = t - t0
            if 5.0 <= ht <= 2000.0:
                holds.append((kid, ht))
    return holds


def digraph_latencies(events: pd.DataFrame) -> list[tuple[str, float]]:
    """Odstęp między kolejnymi down (flight/digraph): keyA>keyB → latency ms."""
    downs = events[events["event_type"] == "down"][["key_id", "elapsed_ms"]]
    pairs: list[tuple[str, float]] = []
    prev_key = None
    prev_t = None
    for _, row in downs.iterrows():
        kid = row["key_id"]
        t = float(row["elapsed_ms"])
        if prev_key is not None and prev_t is not None:
            lat = t - prev_t
            if 5.0 <= lat <= 3000.0:
                pairs.append((f"{prev_key}>{kid}", lat))
        prev_key, prev_t = kid, t
    return pairs


def session_features(events: pd.DataFrame) -> dict[str, float]:
    """Wektor cech dla jednej sesji."""
    feats: dict[str, float] = {}
    holds = hold_times(events)
    digs = digraph_latencies(events)

    hold_by: dict[str, list[float]] = defaultdict(list)
    for k, v in holds:
        hold_by[k].append(v)

    dig_by: dict[str, list[float]] = defaultdict(list)
    for k, v in digs:
        dig_by[k].append(v)

    all_holds = [v for _, v in holds]
    all_digs = [v for _, v in digs]

    feats["hold_mean"] = float(np.mean(all_holds)) if all_holds else 0.0
    feats["hold_std"] = float(np.std(all_holds)) if len(all_holds) > 1 else 0.0
    feats["hold_median"] = float(np.median(all_holds)) if all_holds else 0.0
    feats["flight_mean"] = float(np.mean(all_digs)) if all_digs else 0.0
    feats["flight_std"] = float(np.std(all_digs)) if len(all_digs) > 1 else 0.0
    feats["flight_median"] = float(np.median(all_digs)) if all_digs else 0.0

    for k in COMMON_KEYS:
        vals = hold_by.get(k, [])
        feats[f"hold_{k}"] = float(np.mean(vals)) if vals else feats["hold_mean"]

    for d in COMMON_DIGRAPHS:
        vals = dig_by.get(d, [])
        feats[f"dig_{d}"] = float(np.mean(vals)) if vals else feats["flight_mean"]

    downs = events[events["event_type"] == "down"]
    duration_s = max((float(events["elapsed_ms"].max()) - float(events["elapsed_ms"].min())) / 1000.0, 1e-6)
    # przybliżenie znaków: down bez samych modyfikatorów
    char_downs = downs[~downs["key_id"].isin(["Shift", "Ctrl", "Alt", "Meta", "CapsLock"])]
    n_chars = max(len(char_downs), 1)
    feats["wpm"] = (n_chars / 5.0) / (duration_s / 60.0)

    n_bs = int((downs["key_id"] == "Backspace").sum())
    feats["backspace_pct"] = 100.0 * n_bs / n_chars
    feats["n_events"] = float(len(events))
    feats["n_holds"] = float(len(holds))
    feats["n_digraphs"] = float(len(digs))

    return feats


def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Z all_events.csv (kolumny session_uid, participant_id, ...) buduje X, y, session_ids.
    """
    df = normalize_events(df)
    required = {"session_uid", "participant_id", "event_type", "elapsed_ms"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Brak kolumn w CSV: {sorted(missing)}")

    rows: list[dict[str, Any]] = []
    labels: list[str] = []
    sids: list[str] = []

    for sid, g in df.groupby("session_uid", sort=False):
        pid = str(g["participant_id"].iloc[0])
        feats = session_features(g)
        rows.append(feats)
        labels.append(pid)
        sids.append(str(sid))

    X = pd.DataFrame(rows).fillna(0.0)
    y = pd.Series(labels, name="participant_id")
    sessions = pd.Series(sids, name="session_uid")
    return X, y, sessions
