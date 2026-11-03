import type { SessionPayload, SessionSummary } from "./types";

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

export async function submitSession(
  payload: SessionPayload
): Promise<{ session_uid: string; event_count: number }> {
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

export type IdentifyStatus = {
  ready: boolean;
  n_users: number;
  n_sessions: number;
  users: string[];
  sessions_per_user: Record<string, number>;
  min_sessions_per_user: number;
  message: string;
};

export type IdentifyResult = {
  predicted_participant_id: string;
  ranking: { participant_id: string; score: number }[];
  n_events: number;
  model_users: number;
  model_sessions: number;
};

export async function fetchIdentifyStatus(): Promise<IdentifyStatus> {
  const res = await fetch("/api/identify/status");
  if (!res.ok) throw new Error(await getError(res));
  return res.json();
}

export async function identifySession(payload: {
  events: import("./types").KeystrokeEvent[];
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
