import type { KeystrokeEvent, SessionPayload, SessionSummary } from "./types";

async function getError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    return res.statusText;
  } catch {
    return res.statusText;
  }
}

export async function fetchTasks(): Promise<Record<string, string>> {
  const res = await fetch("/api/tasks");
  if (!res.ok) throw new Error(await getError(res));
  const data = await res.json();
  return data.tasks as Record<string, string>;
}

export async function fetchProtocol(participantId?: string): Promise<{
  ready: boolean;
  min_sessions_per_user: number;
  min_events: number;
  min_duration_ms: number;
  confidence_threshold: number;
  protocol_task_id: string;
  participant: {
    participant_id: string;
    sessions: number;
    remaining: number;
    enrolled: boolean;
    sessions_by_task: Record<string, number>;
    recommended_task: string;
  } | null;
  sessions_per_user: Record<string, number>;
}> {
  const q = participantId ? `?participantId=${encodeURIComponent(participantId)}` : "";
  const res = await fetch(`/api/protocol${q}`);
  if (!res.ok) throw new Error(await getError(res));
  return res.json();
}

export async function submitSession(payload: SessionPayload): Promise<{
  session_uid: string;
  event_count: number;
  protocol?: { sessions: number; remaining: number; enrolled: boolean };
}> {
  const res = await fetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await getError(res));
  return res.json();
}

export async function fetchSessions(adminToken: string): Promise<SessionSummary[]> {
  const res = await fetch("/api/sessions", {
    headers: { "X-Admin-Token": adminToken },
  });
  if (!res.ok) throw new Error(await getError(res));
  return res.json();
}

export function exportSessionUrl(sessionUid: string): string {
  return `/api/sessions/${encodeURIComponent(sessionUid)}/export.csv`;
}

export function exportAllUrl(): string {
  return `/api/export/all.csv`;
}

export function exportMlZipUrl(): string {
  return `/api/export/ml.zip`;
}

export type IdentifyStatus = {
  ready: boolean;
  n_users: number;
  n_sessions: number;
  users: string[];
  sessions_per_user: Record<string, number>;
  min_sessions_per_user: number;
  min_events: number;
  min_duration_ms: number;
  confidence_threshold: number;
  message: string;
};

export type IdentifyResult = {
  predicted_participant_id: string | null;
  identified: boolean;
  confidence: number;
  threshold: number;
  ranking: { participant_id: string; score: number }[];
  n_events: number;
  duration_ms: number;
  model_users: number;
  model_sessions: number;
  message: string;
};

export type VerifyResult = {
  claimed_participant_id: string;
  accepted: boolean;
  score: number;
  threshold: number;
  predicted_participant_id: string;
  ranking: { participant_id: string; score: number }[];
  n_events: number;
  duration_ms: number;
  message: string;
};

export type ModelReport = {
  n_folds: number;
  n_users: number;
  accuracy: number;
  macro_f1: number;
  labels: string[];
  confusion_matrix: number[][];
  sessions_per_user: Record<string, number>;
};

export type DriftReport = {
  users: {
    participant_id: string;
    n_early: number;
    n_late: number;
    hold_mean_early: number;
    hold_mean_late: number;
    flight_mean_early: number;
    flight_mean_late: number;
    wpm_early: number;
    wpm_late: number;
    hold_drift_pct: number;
    flight_drift_pct: number;
    wpm_drift_pct: number;
    environments: string[];
  }[];
  environment_counts: Record<string, number>;
  note: string;
};

export async function fetchIdentifyStatus(): Promise<IdentifyStatus> {
  const res = await fetch("/api/identify/status");
  if (!res.ok) throw new Error(await getError(res));
  return res.json();
}

export async function identifySession(payload: {
  events: KeystrokeEvent[];
  typedText: string;
}): Promise<IdentifyResult> {
  const res = await fetch("/api/identify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await getError(res));
  return res.json();
}

export async function verifySession(payload: {
  claimedParticipantId: string;
  events: KeystrokeEvent[];
  typedText: string;
}): Promise<VerifyResult> {
  const res = await fetch("/api/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await getError(res));
  return res.json();
}

export async function fetchModelReport(token: string): Promise<ModelReport> {
  const res = await fetch("/api/admin/model-report", {
    headers: { "X-Admin-Token": token },
  });
  if (!res.ok) throw new Error(await getError(res));
  return res.json();
}

export async function fetchDriftReport(token: string): Promise<DriftReport> {
  const res = await fetch("/api/admin/drift", {
    headers: { "X-Admin-Token": token },
  });
  if (!res.ok) throw new Error(await getError(res));
  return res.json();
}

export async function downloadAuth(url: string, token: string, filename: string): Promise<void> {
  const res = await fetch(url, { headers: { "X-Admin-Token": token } });
  if (!res.ok) throw new Error(await getError(res));
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(objectUrl);
}
