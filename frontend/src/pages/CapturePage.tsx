import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { fetchProtocol, fetchTasks, submitSession } from "../api";
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
  const [elapsedSec, setElapsedSec] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [keyboardType, setKeyboardType] = useState("laptop");
  const [dominantHand, setDominantHand] = useState("right");
  const [fatigue, setFatigue] = useState(2);
  const [minEvents, setMinEvents] = useState(40);
  const [minDurationSec, setMinDurationSec] = useState(15);
  const [minSessions, setMinSessions] = useState(3);
  const [mySessions, setMySessions] = useState(0);
  const [enrolled, setEnrolled] = useState(false);

  const eventsRef = useRef<KeystrokeEvent[]>([]);
  const startRef = useRef<number | null>(null);
  const capturingRef = useRef(false);
  const areaRef = useRef<HTMLTextAreaElement | null>(null);

  const reference = tasks[taskId] || "";

  function refreshProtocol(pid = participantId) {
    fetchProtocol(pid)
      .then((p) => {
        setMinEvents(p.min_events);
        setMinDurationSec(Math.round(p.min_duration_ms / 1000));
        setMinSessions(p.min_sessions_per_user);
        if (p.participant) {
          setMySessions(p.participant.sessions);
          setEnrolled(p.participant.enrolled);
        }
        if (p.protocol_task_id && !capturingRef.current) {
          // nie nadpisuj wyboru użytkownika przy każdym ticku — tylko gdy brak tasków
        }
      })
      .catch(() => undefined);
  }

  useEffect(() => {
    fetchTasks()
      .then((t) => {
        setTasks(t);
        const keys = Object.keys(t);
        if (keys.length && !keys.includes(taskId)) setTaskId(keys[0]);
      })
      .catch((e: Error) => setError(e.message));
    refreshProtocol();
  }, []);

  useEffect(() => {
    capturingRef.current = phase === "capturing";
  }, [phase]);

  useEffect(() => {
    if (phase !== "capturing" || startRef.current == null) return;
    const id = window.setInterval(() => {
      if (startRef.current != null) {
        setElapsedSec((performance.now() - startRef.current) / 1000);
      }
    }, 200);
    return () => window.clearInterval(id);
  }, [phase]);

  function onParticipantIdChange(value: string) {
    const next = value.trim().toUpperCase();
    setParticipantId(next);
    if (next) {
      saveParticipantId(next);
      refreshProtocol(next);
    }
  }

  function newRandomId() {
    if (phase === "capturing") return;
    const id = generateParticipantId();
    setParticipantId(id);
    saveParticipantId(id);
    refreshProtocol(id);
    setMessage(`Wygenerowano nowe ID: ${id}. Zapamiętaj je na kolejne próby.`);
  }

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
    if (!participantId.trim()) {
      setError("Brak ID uczestnika.");
      return;
    }
    saveParticipantId(participantId.trim());
    setError(null);
    setMessage(null);
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
    if (startRef.current != null) {
      setElapsedSec((performance.now() - startRef.current) / 1000);
    }
  }

  function resetAll() {
    eventsRef.current = [];
    startRef.current = null;
    setEventCount(0);
    setElapsedSec(0);
    setTyped("");
    setPhase("idle");
    setMessage(null);
    setError(null);
  }

  async function sendSession() {
    if (eventsRef.current.length < minEvents) {
      setError(`Za mało zdarzeń (min. ${minEvents}). Pisanie: Start → dłuższy fragment → Stop.`);
      return;
    }
    const durationMs =
      eventsRef.current.length > 0
        ? eventsRef.current[eventsRef.current.length - 1]!.t - eventsRef.current[0]!.t
        : 0;
    if (durationMs < minDurationSec * 1000) {
      setError(`Sesja zbyt krótka (min. ${minDurationSec} s).`);
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
        environment: "web",
        keyboardType,
        dominantHand,
        fatigue,
        durationMs,
        events: eventsRef.current,
      });
      const left = result.protocol?.remaining;
      const done = result.protocol?.enrolled;
      setMySessions(result.protocol?.sessions ?? mySessions + 1);
      setEnrolled(!!done);
      setMessage(
        `Zapisano ${result.session_uid} (${result.event_count} zdarzeń). ID: ${pid}. ` +
          (done
            ? "Enroll ukończony (≥ wymaganych sesji) — możesz użyć Identyfikuj / Weryfikuj."
            : `Do enrollu zostało jeszcze ok. ${left} sesji z tym samym ID.`)
      );
      setPhase("idle");
      eventsRef.current = [];
      setEventCount(0);
      setElapsedSec(0);
      refreshProtocol(pid);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Błąd zapisu");
    } finally {
      setSaving(false);
    }
  }

  const sampleOk = eventCount >= minEvents && elapsedSec >= minDurationSec;

  return (
    <section className="panel">
      <p className="hint">
        Protokół: <strong>{minSessions} sesje</strong> na osobę (to samo ID), najlepiej teksty A/B/C.
        Minimalna próbka: ~{minDurationSec} s i ≥{minEvents} zdarzeń. Potem zakładka{" "}
        <strong>Identyfikuj</strong>.
      </p>

      <div className={`status ${enrolled ? "ok" : ""}`} style={{ marginTop: "1rem" }}>
        Postęp enrollu dla <code>{participantId}</code>:{" "}
        <strong>
          {mySessions}/{minSessions}
        </strong>{" "}
        sesji {enrolled ? "(gotowe)" : "(w toku)"}
      </div>

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
        <button type="button" className="secondary" onClick={newRandomId} disabled={phase === "capturing"}>
          Losuj nowe ID
        </button>
        <p className="hint id-hint">
          <strong>Zapamiętaj ID</strong> na kolejne próby. „Losuj nowe” tylko gdy chcesz nową tożsamość.
        </p>
      </div>

      <div className="grid" style={{ marginTop: "1rem" }}>
        <label>
          Tekst zadania
          <select value={taskId} disabled={phase === "capturing"} onChange={(e) => setTaskId(e.target.value)}>
            {Object.keys(tasks).map((k) => (
              <option key={k} value={k}>
                Tekst {k}
              </option>
            ))}
          </select>
        </label>
        <label>
          Klawiatura
          <select
            value={keyboardType}
            disabled={phase === "capturing"}
            onChange={(e) => setKeyboardType(e.target.value)}
          >
            <option value="laptop">Laptop (wbudowana)</option>
            <option value="external_usb">Zewnętrzna USB</option>
            <option value="other">Inna</option>
          </select>
        </label>
        <label>
          Ręka dominująca
          <select
            value={dominantHand}
            disabled={phase === "capturing"}
            onChange={(e) => setDominantHand(e.target.value)}
          >
            <option value="right">Prawa</option>
            <option value="left">Lewa</option>
            <option value="both">Obie / obieguocznie</option>
          </select>
        </label>
        <label>
          Zmęczenie (1–5)
          <select
            value={fatigue}
            disabled={phase === "capturing"}
            onChange={(e) => setFatigue(Number(e.target.value))}
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
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
          placeholder={phase === "capturing" ? "Pisz tutaj…" : "Kliknij Start"}
        />
      </label>

      <div className="actions">
        <button type="button" onClick={startCapture} disabled={phase === "capturing"}>
          Start
        </button>
        <button type="button" className="secondary" onClick={stopCapture} disabled={phase !== "capturing"}>
          Stop
        </button>
        <button type="button" onClick={sendSession} disabled={saving || !sampleOk}>
          {saving ? "Wysyłanie…" : "Wyślij sesję"}
        </button>
        <button type="button" className="secondary" onClick={resetAll}>
          Wyczyść
        </button>
      </div>

      <div className="meta">
        <span>ID: {participantId || "—"}</span>
        <span>Status: {phase}</span>
        <span>
          Czas: {elapsedSec.toFixed(1)} s / {minDurationSec} s
        </span>
        <span>
          Zdarzenia: {eventCount} / {minEvents}
        </span>
        <span>{sampleOk ? "Próbka OK" : "Za krótko"}</span>
      </div>

      {message && <div className="status ok">{message}</div>}
      {error && <div className="status error">{error}</div>}
    </section>
  );
}
