import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { fetchIdentifyStatus, fetchTasks, identifySession, type IdentifyResult, type IdentifyStatus } from "../api";
import type { KeystrokeEvent } from "../types";

type Phase = "idle" | "capturing" | "done";

export default function IdentifyPage() {
  const [tasks, setTasks] = useState<Record<string, string>>({});
  const [taskId, setTaskId] = useState("A");
  const [typed, setTyped] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [eventCount, setEventCount] = useState(0);
  const [status, setStatus] = useState<IdentifyStatus | null>(null);
  const [result, setResult] = useState<IdentifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const eventsRef = useRef<KeystrokeEvent[]>([]);
  const startRef = useRef<number | null>(null);
  const capturingRef = useRef(false);
  const areaRef = useRef<HTMLTextAreaElement | null>(null);

  const reference = tasks[taskId] || "";

  function refreshStatus() {
    fetchIdentifyStatus()
      .then(setStatus)
      .catch((e: Error) => setError(e.message));
  }

  useEffect(() => {
    fetchTasks()
      .then((t) => {
        setTasks(t);
        const keys = Object.keys(t);
        if (keys.length) setTaskId(keys[0]);
      })
      .catch((e: Error) => setError(e.message));
    refreshStatus();
  }, []);

  useEffect(() => {
    capturingRef.current = phase === "capturing";
  }, [phase]);

  function pushEvent(type: "down" | "up", e: KeyboardEvent) {
    if (!capturingRef.current) return;
    if (startRef.current == null) startRef.current = performance.now();
    eventsRef.current.push({
      t: performance.now() - startRef.current,
      type,
      code: e.code || "",
      key: e.key || "",
      keyCode: e.keyCode || 0,
      shift: e.shiftKey,
      ctrl: e.ctrlKey,
      alt: e.altKey,
    });
    setEventCount(eventsRef.current.length);
  }

  function startCapture() {
    setError(null);
    setResult(null);
    eventsRef.current = [];
    startRef.current = null;
    setEventCount(0);
    setTyped("");
    setPhase("capturing");
    setTimeout(() => areaRef.current?.focus(), 0);
  }

  function stopCapture() {
    setPhase("done");
  }

  async function runIdentify() {
    if (eventsRef.current.length < 20) {
      setError("Za mało danych — napisz dłuższy fragment (Start → pisz → Stop).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await identifySession({
        events: eventsRef.current,
        typedText: typed,
      });
      setResult(res);
      refreshStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Błąd identyfikacji");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2 style={{ marginTop: 0, fontFamily: "IBM Plex Serif, Georgia, serif" }}>
        Identyfikuj uczestnika na podstawie dynamiki pisania
      </h2>
      <p className="hint">
        Najpierw zbierz <strong>kilka sesji</strong> od każdej osoby (to samo ID na stronie
        „Sesja uczestnika”). Potem tutaj wpisz próbkę <em>bez</em> podawania ID — system
        zgadnie, kto pisał.
      </p>

      {status && (
        <div className={`status ${status.ready ? "ok" : ""}`} style={{ marginTop: "1rem" }}>
          {status.ready ? (
            <>
              Model gotowy: <strong>{status.n_users}</strong> uczestników,{" "}
              <strong>{status.n_sessions}</strong> sesji treningowych.
            </>
          ) : (
            <>
              Model jeszcze niegotowy. {status.message}
              <br />
              Potrzeba ≥{status.min_sessions_per_user} sesji na osobę (obecnie:{" "}
              {Object.entries(status.sessions_per_user)
                .map(([u, n]) => `${u}×${n}`)
                .join(", ") || "brak"}
              ).
            </>
          )}
        </div>
      )}

      <div className="grid" style={{ marginTop: "1rem" }}>
        <label>
          Tekst do przepisania (próbka testowa)
          <select
            value={taskId}
            disabled={phase === "capturing"}
            onChange={(e) => setTaskId(e.target.value)}
          >
            {Object.keys(tasks).map((k) => (
              <option key={k} value={k}>
                Tekst {k}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label style={{ marginTop: "1rem" }}>
        Wzorzec
        <textarea className="reference" readOnly value={reference} />
      </label>

      <label style={{ marginTop: "1rem" }}>
        Pole wpisywania (bez podawania ID)
        <textarea
          ref={areaRef}
          className="typed"
          value={typed}
          disabled={phase !== "capturing"}
          onChange={(e) => setTyped(e.target.value)}
          onKeyDown={(e) => pushEvent("down", e)}
          onKeyUp={(e) => pushEvent("up", e)}
          placeholder={phase === "capturing" ? "Pisz tutaj…" : "Start → przepisz tekst → Stop → Identyfikuj"}
        />
      </label>

      <div className="actions">
        <button type="button" onClick={startCapture} disabled={phase === "capturing"}>
          Start
        </button>
        <button
          type="button"
          className="secondary"
          onClick={stopCapture}
          disabled={phase !== "capturing"}
        >
          Stop
        </button>
        <button type="button" onClick={runIdentify} disabled={busy || eventCount < 20}>
          {busy ? "Identyfikacja…" : "Identyfikuj"}
        </button>
        <button type="button" className="secondary" onClick={refreshStatus}>
          Odśwież model
        </button>
      </div>

      <div className="meta">
        <span>Status: {phase}</span>
        <span>Zdarzenia: {eventCount}</span>
      </div>

      {error && <div className="status error">{error}</div>}

      {result && (
        <div className="status ok" style={{ marginTop: "1rem" }}>
          <p style={{ margin: "0 0 0.75rem" }}>
            Najbardziej podobny uczestnik:{" "}
            <strong style={{ fontSize: "1.25rem" }}>{result.predicted_participant_id}</strong>
          </p>
          <p className="hint" style={{ margin: "0 0 0.5rem" }}>
            Ranking (prawdopodobieństwo / podobieństwo):
          </p>
          <ol style={{ margin: 0, paddingLeft: "1.25rem" }}>
            {result.ranking.map((h) => (
              <li key={h.participant_id}>
                <code>{h.participant_id}</code> — {(h.score * 100).toFixed(1)}%
              </li>
            ))}
          </ol>
          <p className="hint" style={{ margin: "0.75rem 0 0" }}>
            Na podstawie {result.n_events} zdarzeń; model: {result.model_users} osób /{" "}
            {result.model_sessions} sesji.
          </p>
        </div>
      )}
    </section>
  );
}
