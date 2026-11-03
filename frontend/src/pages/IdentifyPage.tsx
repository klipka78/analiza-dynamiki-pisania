import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import {
  fetchIdentifyStatus,
  fetchTasks,
  identifySession,
  verifySession,
  type IdentifyResult,
  type IdentifyStatus,
  type VerifyResult,
} from "../api";
import { loadOrCreateParticipantId } from "../participantId";
import type { KeystrokeEvent } from "../types";

type Phase = "idle" | "capturing" | "done";
type Mode = "identify" | "verify";

export default function IdentifyPage() {
  const [tasks, setTasks] = useState<Record<string, string>>({});
  const [taskId, setTaskId] = useState("A");
  const [typed, setTyped] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [mode, setMode] = useState<Mode>("identify");
  const [claimedId, setClaimedId] = useState(() => loadOrCreateParticipantId());
  const [eventCount, setEventCount] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [status, setStatus] = useState<IdentifyStatus | null>(null);
  const [idResult, setIdResult] = useState<IdentifyResult | null>(null);
  const [verResult, setVerResult] = useState<VerifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const eventsRef = useRef<KeystrokeEvent[]>([]);
  const startRef = useRef<number | null>(null);
  const capturingRef = useRef(false);
  const areaRef = useRef<HTMLTextAreaElement | null>(null);

  const reference = tasks[taskId] || "";
  const minEvents = status?.min_events ?? 40;
  const minDurationSec = Math.round((status?.min_duration_ms ?? 15000) / 1000);

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

  useEffect(() => {
    if (phase !== "capturing" || startRef.current == null) return;
    const id = window.setInterval(() => {
      if (startRef.current != null) setElapsedSec((performance.now() - startRef.current) / 1000);
    }, 200);
    return () => window.clearInterval(id);
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
    setIdResult(null);
    setVerResult(null);
    eventsRef.current = [];
    startRef.current = null;
    setEventCount(0);
    setElapsedSec(0);
    setTyped("");
    setPhase("capturing");
    setTimeout(() => areaRef.current?.focus(), 0);
  }

  function stopCapture() {
    setPhase("done");
  }

  async function run() {
    if (!status?.ready) {
      setError("Model niegotowy — zbierz więcej sesji enroll (Sesja uczestnika).");
      return;
    }
    if (eventsRef.current.length < minEvents || elapsedSec < minDurationSec) {
      setError(`Za krótka próbka (min. ${minDurationSec} s i ${minEvents} zdarzeń).`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (mode === "identify") {
        setIdResult(await identifySession({ events: eventsRef.current, typedText: typed }));
      } else {
        setVerResult(
          await verifySession({
            claimedParticipantId: claimedId.trim(),
            events: eventsRef.current,
            typedText: typed,
          })
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Błąd");
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
        <strong>1:N Identyfikacja</strong> — kto pisał?{" "}
        <strong>1:1 Weryfikacja</strong> — czy to nadal wskazane ID? Przy niskiej pewności:
        „niezidentyfikowano” / odrzucenie.
      </p>

      {status && (
        <div className={`status ${status.ready ? "ok" : ""}`} style={{ marginTop: "1rem" }}>
          {status.ready ? (
            <>
              Model gotowy: {status.n_users} osób, {status.n_sessions} sesji. Próg pewności:{" "}
              {(status.confidence_threshold * 100).toFixed(0)}%.
            </>
          ) : (
            <>Model niegotowy. {status.message}</>
          )}
        </div>
      )}

      <div className="actions" style={{ marginTop: "1rem" }}>
        <button
          type="button"
          className={mode === "identify" ? undefined : "secondary"}
          onClick={() => setMode("identify")}
        >
          Identyfikacja 1:N
        </button>
        <button
          type="button"
          className={mode === "verify" ? undefined : "secondary"}
          onClick={() => setMode("verify")}
        >
          Weryfikacja 1:1
        </button>
      </div>

      {mode === "verify" && (
        <label style={{ marginTop: "1rem", maxWidth: 360 }}>
          Claimed ID (czy to nadal ta osoba?)
          <input value={claimedId} onChange={(e) => setClaimedId(e.target.value.toUpperCase())} />
        </label>
      )}

      <div className="grid" style={{ marginTop: "1rem" }}>
        <label>
          Tekst próbki
          <select value={taskId} disabled={phase === "capturing"} onChange={(e) => setTaskId(e.target.value)}>
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
        Pole wpisywania
        <textarea
          ref={areaRef}
          className="typed"
          value={typed}
          disabled={phase !== "capturing"}
          onChange={(e) => setTyped(e.target.value)}
          onKeyDown={(e) => pushEvent("down", e)}
          onKeyUp={(e) => pushEvent("up", e)}
          placeholder="Start → przepisz → Stop → uruchom"
        />
      </label>

      <div className="actions">
        <button type="button" onClick={startCapture} disabled={phase === "capturing"}>
          Start
        </button>
        <button type="button" className="secondary" onClick={stopCapture} disabled={phase !== "capturing"}>
          Stop
        </button>
        <button type="button" onClick={run} disabled={busy || !status?.ready}>
          {busy ? "Liczenie…" : mode === "identify" ? "Identyfikuj" : "Weryfikuj"}
        </button>
        <button type="button" className="secondary" onClick={refreshStatus}>
          Odśwież model
        </button>
      </div>

      <div className="meta">
        <span>
          Czas: {elapsedSec.toFixed(1)}/{minDurationSec} s
        </span>
        <span>
          Zdarzenia: {eventCount}/{minEvents}
        </span>
      </div>

      {error && <div className="status error">{error}</div>}

      {idResult && (
        <div className={`status ${idResult.identified ? "ok" : "error"}`} style={{ marginTop: "1rem" }}>
          <p style={{ margin: "0 0 0.5rem" }}>{idResult.message}</p>
          {idResult.identified && (
            <p style={{ margin: "0 0 0.75rem", fontSize: "1.2rem" }}>
              <strong>{idResult.predicted_participant_id}</strong> (
              {(idResult.confidence * 100).toFixed(1)}%)
            </p>
          )}
          <ol style={{ margin: 0, paddingLeft: "1.25rem" }}>
            {idResult.ranking.map((h) => (
              <li key={h.participant_id}>
                <code>{h.participant_id}</code> — {(h.score * 100).toFixed(1)}%
              </li>
            ))}
          </ol>
        </div>
      )}

      {verResult && (
        <div className={`status ${verResult.accepted ? "ok" : "error"}`} style={{ marginTop: "1rem" }}>
          <p style={{ margin: 0, fontSize: "1.15rem" }}>
            <strong>{verResult.accepted ? "TAK" : "NIE"}</strong> — {verResult.message}
          </p>
          <p className="hint" style={{ margin: "0.5rem 0 0" }}>
            Score {verResult.claimed_participant_id}: {(verResult.score * 100).toFixed(1)}% (próg{" "}
            {(verResult.threshold * 100).toFixed(0)}%)
          </p>
        </div>
      )}
    </section>
  );
}
