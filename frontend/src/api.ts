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
