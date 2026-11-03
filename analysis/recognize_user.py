#!/usr/bin/env python3
"""
Rozpoznawanie autora na podstawie dynamiki pisania (keystroke dynamics).

Wejście: eksport z systemu pismo
  - panel /admin → „Eksport wszystkich zdarzeń” → all_events.csv
  - albo GET /api/export/all.csv (header X-Admin-Token)

Użycie:
  pip install -r requirements.txt
  python recognize_user.py --csv path/to/all_events.csv
  python recognize_user.py --demo          # sztuczne dane (smoke test)
  python recognize_user.py --csv all_events.csv --model rf --out-dir results
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC

from features import build_feature_matrix


def load_all_events(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # eksport WEB ma session_uid + participant_id
    if "session_uid" not in df.columns:
        raise ValueError(
            "Oczekiwany plik all_events.csv z kolumnami session_uid, participant_id, ...\n"
            "Pobierz: /admin → Eksport wszystkich zdarzeń"
        )
    return df


def make_demo_csv(path: Path, n_users: int = 5, sessions_per_user: int = 8) -> Path:
    """Generuje syntetyczne all_events.csv z różnymi profilami hold/flight per user."""
    rng = np.random.default_rng(42)
    keys = ["KeyA", "KeyN", "KeyA", "KeyL", "KeyI", "KeyZ", "KeyA", "Space", "KeyT", "KeyE", "KeyK", "KeyS", "KeyT"]
    rows: list[dict] = []
    seq_global = 0

    for u in range(1, n_users + 1):
        pid = f"P{u:03d}"
        # unikalny „charakter” pisania
        hold_mu = 70 + u * 18
        flight_mu = 90 + u * 25
        for s in range(1, sessions_per_user + 1):
            sid = f"demo_{pid}_S{s}"
            t = 0.0
            seq = 0
            # lekki szum między sesjami tej samej osoby
            h_mu = hold_mu + rng.normal(0, 5)
            f_mu = flight_mu + rng.normal(0, 8)
            for k in keys * 3:
                seq += 1
                t += max(20.0, rng.normal(f_mu, 25))
                rows.append(
                    {
                        "session_uid": sid,
                        "participant_id": pid,
                        "task_id": "A",
                        "seq": seq,
                        "elapsed_ms": f"{t:.3f}",
                        "event_type": "down",
                        "code": k,
                        "key": k.replace("Key", "").lower() if k.startswith("Key") else " ",
                        "key_code": 0,
                        "shift": 0,
                        "ctrl": 0,
                        "alt": 0,
                    }
                )
                seq += 1
                hold = max(15.0, rng.normal(h_mu, 15))
                t += hold
                rows.append(
                    {
                        "session_uid": sid,
                        "participant_id": pid,
                        "task_id": "A",
                        "seq": seq,
                        "elapsed_ms": f"{t:.3f}",
                        "event_type": "up",
                        "code": k,
                        "key": k.replace("Key", "").lower() if k.startswith("Key") else " ",
                        "key_code": 0,
                        "shift": 0,
                        "ctrl": 0,
                        "alt": 0,
                    }
                )
                # okazjonalny Backspace
                if rng.random() < 0.03 + u * 0.01:
                    seq += 1
                    t += max(20.0, rng.normal(f_mu, 20))
                    rows.append(
                        {
                            "session_uid": sid,
                            "participant_id": pid,
                            "task_id": "A",
                            "seq": seq,
                            "elapsed_ms": f"{t:.3f}",
                            "event_type": "down",
                            "code": "Backspace",
                            "key": "Backspace",
                            "key_code": 8,
                            "shift": 0,
                            "ctrl": 0,
                            "alt": 0,
                        }
                    )
                    seq += 1
                    t += max(15.0, rng.normal(h_mu, 10))
                    rows.append(
                        {
                            "session_uid": sid,
                            "participant_id": pid,
                            "task_id": "A",
                            "seq": seq,
                            "elapsed_ms": f"{t:.3f}",
                            "event_type": "up",
                            "code": "Backspace",
                            "key": "Backspace",
                            "key_code": 8,
                            "shift": 0,
                            "ctrl": 0,
                            "alt": 0,
                        }
                    )
            seq_global += seq

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def make_classifier(name: str) -> Pipeline:
    name = name.lower()
    if name == "rf":
        clf = RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_leaf=1,
            random_state=42,
            class_weight="balanced",
        )
        return Pipeline([("clf", clf)])
    if name == "svm":
        clf = SVC(kernel="rbf", C=2.0, gamma="scale", class_weight="balanced")
        return Pipeline([("scaler", StandardScaler()), ("clf", clf)])
    if name == "knn":
        clf = KNeighborsClassifier(n_neighbors=3, weights="distance", metric="manhattan")
        return Pipeline([("scaler", StandardScaler()), ("clf", clf)])
    raise ValueError("model musi być: rf | svm | knn")


def train_eval(
    X: pd.DataFrame,
    y: pd.Series,
    sessions: pd.Series,
    model_name: str,
    test_size: float,
    out_dir: Path,
) -> dict:
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    # split PO SESJACH (GroupShuffleSplit) — sesja nie trafia jednocześnie do train i test
    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=42)
    train_idx, test_idx = next(gss.split(X, y_enc, groups=sessions))

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y_enc[train_idx], y_enc[test_idx]

    pipe = make_classifier(model_name)
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    labels_present = sorted(set(y_test) | set(y_pred))
    cm = confusion_matrix(y_test, y_pred, labels=labels_present)
    report = classification_report(
        y_test,
        y_pred,
        labels=labels_present,
        target_names=le.inverse_transform(labels_present),
        zero_division=0,
    )

    out_dir.mkdir(parents=True, exist_ok=True)

    # macierz pomyłek
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=le.inverse_transform(labels_present),
        yticklabels=le.inverse_transform(labels_present),
        ax=ax,
    )
    ax.set_xlabel("Predykcja")
    ax.set_ylabel("Prawda")
    ax.set_title(f"Macierz pomyłek ({model_name}) — accuracy={acc:.3f}")
    fig.tight_layout()
    cm_path = out_dir / f"confusion_{model_name}.png"
    fig.savefig(cm_path, dpi=140)
    plt.close(fig)

    # zapis cech sesji
    feat_path = out_dir / "session_features.csv"
    feat_df = X.copy()
    feat_df.insert(0, "participant_id", y.values)
    feat_df.insert(0, "session_uid", sessions.values)
    feat_df.to_csv(feat_path, index=False)

    metrics = {
        "model": model_name,
        "n_sessions": int(len(sessions)),
        "n_users": int(y.nunique()),
        "n_train_sessions": int(len(train_idx)),
        "n_test_sessions": int(len(test_idx)),
        "accuracy": float(acc),
        "macro_f1": float(f1),
        "confusion_matrix_png": str(cm_path),
        "features_csv": str(feat_path),
        "classification_report": report,
    }
    (out_dir / f"metrics_{model_name}.json").write_text(
        json.dumps({k: v for k, v in metrics.items() if k != "classification_report"}, indent=2),
        encoding="utf-8",
    )
    (out_dir / f"report_{model_name}.txt").write_text(report, encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Rozpoznawanie użytkownika (keystroke dynamics)")
    parser.add_argument("--csv", type=Path, help="Ścieżka do all_events.csv z systemu")
    parser.add_argument("--demo", action="store_true", help="Użyj syntetycznych danych demo")
    parser.add_argument("--model", choices=["rf", "svm", "knn", "all"], default="all")
    parser.add_argument("--test-size", type=float, default=0.3, help="Udział sesji testowych")
    parser.add_argument("--out-dir", type=Path, default=Path("results"))
    parser.add_argument("--min-sessions-per-user", type=int, default=2)
    args = parser.parse_args()

    if args.demo:
        demo_path = Path(__file__).resolve().parent / "data" / "demo_all_events.csv"
        csv_path = make_demo_csv(demo_path)
        print(f"[demo] Wygenerowano: {csv_path}")
    elif args.csv:
        csv_path = args.csv
    else:
        parser.error("Podaj --csv all_events.csv albo --demo")

    df = load_all_events(csv_path)
    print(f"Wczytano eventów: {len(df)}, sesji: {df['session_uid'].nunique()}, "
          f"użytkowników: {df['participant_id'].nunique()}")

    X, y, sessions = build_feature_matrix(df)

    # odfiltruj użytkowników z zbyt małą liczbą sesji
    counts = y.value_counts()
    keep_users = counts[counts >= args.min_sessions_per_user].index
    mask = y.isin(keep_users)
    X, y, sessions = X.loc[mask].reset_index(drop=True), y.loc[mask].reset_index(drop=True), sessions.loc[mask].reset_index(drop=True)

    if y.nunique() < 2:
        raise SystemExit(
            "Potrzeba ≥2 użytkowników z wystarczającą liczbą sesji. "
            f"min-sessions-per-user={args.min_sessions_per_user}"
        )
    if len(X) < 4:
        raise SystemExit("Za mało sesji do sensownego split train/test.")

    print(f"Macierz cech: {X.shape[0]} sesji × {X.shape[1]} cech, klas: {y.nunique()}")

    models = ["rf", "svm", "knn"] if args.model == "all" else [args.model]
    for m in models:
        print(f"\n=== Model: {m} ===")
        metrics = train_eval(X, y, sessions, m, args.test_size, args.out_dir)
        print(f"Accuracy: {metrics['accuracy']:.3f}  |  macro-F1: {metrics['macro_f1']:.3f}")
        print(f"Train sessions: {metrics['n_train_sessions']}  Test: {metrics['n_test_sessions']}")
        print(metrics["classification_report"])
        print(f"Zapisano: {metrics['confusion_matrix_png']}")


if __name__ == "__main__":
    main()
