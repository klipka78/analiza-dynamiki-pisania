import { useState } from "react";
import {
  downloadAuth,
  exportAllUrl,
  exportMlZipUrl,
  exportSessionUrl,
  fetchDriftReport,
  fetchModelReport,
  fetchSessions,
  type DriftReport,
  type ModelReport,
} from "../api";
import type { SessionSummary } from "../types";

export default function AdminPage() {
  const [token, setToken] = useState(() => localStorage.getItem("adminToken") || "");
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [report, setReport] = useState<ModelReport | null>(null);
  const [drift, setDrift] = useState<DriftReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      localStorage.setItem("adminToken", token);
      setSessions(await fetchSessions(token));
    } catch (e) {
      setSessions([]);
      setError(e instanceof Error ? e.message : "Błąd");
    } finally {
      setLoading(false);
    }
  }

  async function loadReport() {
    setError(null);
    try {
      localStorage.setItem("adminToken", token);
      setReport(await fetchModelReport(token));
    } catch (e) {
      setReport(null);
      setError(e instanceof Error ? e.message : "Błąd raportu");
    }
  }

  async function loadDrift() {
    setError(null);
    try {
      localStorage.setItem("adminToken", token);
      setDrift(await fetchDriftReport(token));
    } catch (e) {
      setDrift(null);
      setError(e instanceof Error ? e.message : "Błąd drift");
    }
  }

  async function download(url: string, filename: string) {
    try {
      await downloadAuth(url, token, filename);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Błąd eksportu");
    }
  }

  return (
    <section className="panel">
      <p className="hint">Panel badacza: lista sesji i eksport CSV</p>

      <label style={{ marginTop: "1rem", maxWidth: 360 }}>
        Token admina
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          autoComplete="off"
        />
      </label>

      <div className="actions">
        <button type="button" onClick={load} disabled={loading || !token}>
          {loading ? "Ładowanie…" : "Odśwież listę"}
        </button>
        <button type="button" className="secondary" onClick={() => download(exportAllUrl(), "all_events.csv")} disabled={!token}>
          Eksport CSV
        </button>
        <button type="button" className="secondary" onClick={() => download(exportMlZipUrl(), "pismo_ml_export.zip")} disabled={!token}>
          Eksport ZIP (ML)
        </button>
        <button type="button" className="secondary" onClick={loadReport} disabled={!token}>
          Raport LOSO
        </button>
        <button type="button" className="secondary" onClick={loadDrift} disabled={!token}>
          Stabilność / drift
        </button>
      </div>

      {error && <div className="status error">{error}</div>}

      {report && (
        <div className="status ok" style={{ marginTop: "1rem" }}>
          <p style={{ margin: "0 0 0.5rem" }}>
            <strong>Leave-one-session-out</strong>: accuracy {(report.accuracy * 100).toFixed(1)}%,
            macro-F1 {(report.macro_f1 * 100).toFixed(1)}%, foldów {report.n_folds}, użytkowników{" "}
            {report.n_users}
          </p>
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th></th>
                  {report.labels.map((l) => (
                    <th key={l}>{l}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {report.confusion_matrix.map((row, i) => (
                  <tr key={report.labels[i]}>
                    <th>{report.labels[i]}</th>
                    {row.map((v, j) => (
                      <td key={j}>{v}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {drift && (
        <div style={{ marginTop: "1rem" }}>
          <p className="hint">{drift.note}</p>
          <p className="hint">
            Środowiska:{" "}
            {Object.entries(drift.environment_counts)
              .map(([k, v]) => `${k}=${v}`)
              .join(", ") || "—"}{" "}
            (web vs word)
          </p>
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Uczestnik</th>
                  <th>Δ hold %</th>
                  <th>Δ flight %</th>
                  <th>Δ WPM %</th>
                  <th>Env</th>
                </tr>
              </thead>
              <tbody>
                {drift.users.map((u) => (
                  <tr key={u.participant_id}>
                    <td>{u.participant_id}</td>
                    <td>{u.hold_drift_pct.toFixed(1)}</td>
                    <td>{u.flight_drift_pct.toFixed(1)}</td>
                    <td>{u.wpm_drift_pct.toFixed(1)}</td>
                    <td>{u.environments.join(",")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div style={{ marginTop: "1.25rem", overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              <th>UID</th>
              <th>Uczestnik</th>
              <th>Zadanie</th>
              <th>Env</th>
              <th>Klawiatura</th>
              <th>Zmęczenie</th>
              <th>Zdarzenia</th>
              <th>Data</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id}>
                <td>{s.session_uid}</td>
                <td>{s.participant_id}</td>
                <td>{s.task_id}</td>
                <td>{s.environment || "web"}</td>
                <td>{s.keyboard_type || "—"}</td>
                <td>{s.fatigue || "—"}</td>
                <td>{s.event_count}</td>
                <td>{new Date(s.created_at).toLocaleString()}</td>
                <td>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => download(exportSessionUrl(s.session_uid), `${s.session_uid}.csv`)}
                  >
                    CSV
                  </button>
                </td>
              </tr>
            ))}
            {sessions.length === 0 && (
              <tr>
                <td colSpan={9}>Brak sesji (lub nie załadowano).</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
