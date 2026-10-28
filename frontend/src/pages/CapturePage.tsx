import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { fetchTasks, submitSession } from "../api";
import type { KeystrokeEvent } from "../types";

type Phase = "idle" | "capturing" | "done";

export default function CapturePage() {
  const [tasks, setTasks] = useState<Record<string, string>>({});
  const [participantId, setParticipantId] = useState("P001");
  const [taskId, setTaskId] = useState("A");
  const [typed, setTyped] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [eventCount, setEventCount] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const eventsRef = useRef<KeystrokeEvent[]>([]);
  const startRef = useRef<number | null>(null);
  const capturingRef = useRef(false);
  const areaRef = useRef<HTMLTextAreaElement | null>(null);

  const reference = tasks[taskId] || "";

  useEffect(() => {
    fetchTasks()
      .then((t) => {
        setTasks(t);
        const keys = Object.keys(t);
        if (keys.length && !keys.includes(taskId)) setTaskId(keys[0]);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    capturingRef.current = phase === "capturing";
  }, [phase]);

  function pushEvent(type: "down" | "up", e: KeyboardEvent) {
    if (!capturingRef.current) return;
    if (startRef.current == null) startRef.current = performance.now();
    const t = performance.now() - startRef.current;
    eventsRef.current.push({
      t,
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
    if (!participantId.trim()) {
      setError("Podaj identyfikator uczestnika.");
      return;
    }
    setError(null);
    setMessage(null);
    eventsRef.current = [];
    startRef.current = null;
    setEventCount(0);
    setTyped("");
    setPhase("capturing");
    setTimeout(() => areaRef.current?.focus(), 0);
  }

  function stopCapture() {
    setPhase("done");
    setMessage(`Zatrzymano. Zdarzenia: ${eventsRef.current.length}. Możesz wysłać sesję.`);
  }

  function resetAll() {
    eventsRef.current = [];
    startRef.current = null;
    setEventCount(0);
    setTyped("");
    setPhase("idle");
    setMessage(null);
    setError(null);
  }

  async function sendSession() {
    if (eventsRef.current.length === 0) {
      setError("Brak zdarzeń do wysłania.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const result = await submitSession({
        participantId: participantId.trim(),
        taskId,
        referenceText: reference,
        typedText: typed,
        keyboardLayout: "",
        language: navigator.language || "",
        userAgent: navigator.userAgent || "",
        events: eventsRef.current,
      });
      setMessage(`Zapisano sesję ${result.session_uid} (${result.event_count} zdarzeń).`);
      setPhase("idle");
      eventsRef.current = [];
      setEventCount(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Błąd zapisu");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <p className="hint">
        Przepisuj tekst naturalnym tempem. Poprawki (Backspace) są dozwolone.
        Rejestrowane są wyłącznie czasy i kody klawiszy w tej sesji.
      </p>

      <div className="grid" style={{ marginTop: "1rem" }}>
        <label>
          ID uczestnika
          <input
            value={participantId}
            disabled={phase === "capturing"}
            onChange={(e) => setParticipantId(e.target.value)}
            autoComplete="off"
          />
        </label>
        <label>
          Tekst zadania
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
        Tekst do przepisania
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
          placeholder={phase === "capturing" ? "Pisz tutaj…" : "Kliknij Start, aby zacząć"}
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
        <button type="button" onClick={sendSession} disabled={saving || eventCount === 0}>
          {saving ? "Wysyłanie…" : "Wyślij sesję"}
        </button>
        <button type="button" className="secondary" onClick={resetAll}>
          Wyczyść
        </button>
      </div>

      <div className="meta">
        <span>Status: {phase}</span>
        <span>Zdarzenia: {eventCount}</span>
        <span>Znaków: {typed.length}</span>
      </div>

      {message && <div className="status ok">{message}</div>}
      {error && <div className="status error">{error}</div>}
    </section>
  );
}
