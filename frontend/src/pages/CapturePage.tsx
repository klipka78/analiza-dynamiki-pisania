import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { fetchTasks, submitSession } from "../api";
import {
  generateParticipantId,
  loadOrCreateParticipantId,
  saveParticipantId,
} from "../participantId";
import type { KeystrokeEvent } from "../types";

type Phase = "idle" | "capturing" | "done";

export default function CapturePage() {
  const [tasks, setTasks] = useState<Record<string, string>>({});
  const [participantId, setParticipantId] = useState(() => loadOrCreateParticipantId());
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

  function onParticipantIdChange(value: string) {
    const next = value.trim().toUpperCase();
    setParticipantId(next);
    if (next) saveParticipantId(next);
  }

  function newRandomId() {
    if (phase === "capturing") return;
    const id = generateParticipantId();
    setParticipantId(id);
    saveParticipantId(id);
    setMessage(`Wygenerowano nowe ID: ${id}. Zapamiętaj je na kolejne próby.`);
  }

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
      setError("Brak ID uczestnika — wygeneruj lub wpisz kod.");
      return;
    }
    saveParticipantId(participantId.trim());
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
      const pid = participantId.trim();
      saveParticipantId(pid);
      const result = await submitSession({
        participantId: pid,
        taskId,
        referenceText: reference,
        typedText: typed,
        keyboardLayout: "",
        language: navigator.language || "",
        userAgent: navigator.userAgent || "",
        events: eventsRef.current,
      });
      setMessage(
        `Zapisano sesję ${result.session_uid} (${result.event_count} zdarzeń). ` +
          `Twoje ID: ${pid} — użyj tego samego kodu przy następnej próbie.`
      );
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
        Zrób <strong>kilka sesji</strong> z tym samym ID (różne teksty / dni) — potem w
        zakładce <strong>Identyfikuj</strong> system sprawdzi, czy rozpozna autora.
      </p>

      <div className="id-box" style={{ marginTop: "1rem" }}>
        <label>
          Twój kod uczestnika
          <input
            value={participantId}
            disabled={phase === "capturing"}
            onChange={(e) => onParticipantIdChange(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        <button
          type="button"
          className="secondary"
          onClick={newRandomId}
          disabled={phase === "capturing"}
        >
          Losuj nowe ID
        </button>
        <p className="hint id-hint">
          Kod jest losowy (np. <code>U-K7M2QX</code>) i zapisywany w tej przeglądarce.
          <strong> Zapamiętaj go</strong> albo zapisz — przy kolejnej próbie (inny tekst / inny
          dzień) wpisz <strong>to samo ID</strong>, żeby połączyć sesje w analizie.
        </p>
      </div>

      <div className="grid" style={{ marginTop: "1rem" }}>
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
        <span>ID: {participantId || "—"}</span>
        <span>Status: {phase}</span>
        <span>Zdarzenia: {eventCount}</span>
        <span>Znaków: {typed.length}</span>
      </div>

      {message && <div className="status ok">{message}</div>}
      {error && <div className="status error">{error}</div>}
    </section>
  );
}
