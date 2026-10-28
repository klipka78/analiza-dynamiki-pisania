import { useState } from "react";
import { exportAllUrl, exportSessionUrl, fetchSessions } from "../api";
import type { SessionSummary } from "../types";

export default function AdminPage() {
  const [token, setToken] = useState(() => localStorage.getItem("adminToken") || "");
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      localStorage.setItem("adminToken", token);
      const rows = await fetchSessions(token);
      setSessions(rows);
    } catch (e) {
      setSessions([]);
      setError(e instanceof Error ? e.message : "Błąd");
    } finally {
      setLoading(false);
    }
  }

  function download(url: string) {
    const a = document.createElement("a");
    a.href = url;
    // token via fetch blob for auth header
    fetch(url, { headers: { "X-Admin-Token": token } })
      .then(async (res) => {
        if (!res.ok) throw new Error("Unauthorized / błąd eksportu");
        const blob = await res.blob();
        const objectUrl = URL.createObjectURL(blob);
        a.href = objectUrl;
        a.download = url.includes("all.csv") ? "all_events.csv" : "session.csv";
        a.click();
        URL.revokeObjectURL(objectUrl);
      })
      .catch((e: Error) => setError(e.message));
  }

  return (
    <section className="panel">
      <p className="hint">
        Panel badacza: lista sesji i eksport CSV (ten sam format co makro Word).
        Token ustawiasz w pliku <code>.env</code> jako <code>ADMIN_TOKEN</code>.
      </p>

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
        <button
          type="button"
          className="secondary"
          onClick={() => download(exportAllUrl())}
          disabled={!token}
        >
          Eksport wszystkich zdarzeń
        </button>
      </div>

      {error && <div className="status error">{error}</div>}

      <div style={{ marginTop: "1.25rem", overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              <th>UID</th>
              <th>Uczestnik</th>
              <th>Zadanie</th>
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
                <td>{s.event_count}</td>
                <td>{new Date(s.created_at).toLocaleString()}</td>
                <td>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => download(exportSessionUrl(s.session_uid))}
                  >
                    CSV
                  </button>
                </td>
              </tr>
            ))}
            {sessions.length === 0 && (
              <tr>
                <td colSpan={6}>Brak sesji (lub nie załadowano).</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
