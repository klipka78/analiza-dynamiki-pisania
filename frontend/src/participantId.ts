const STORAGE_KEY = "pismo_participant_id";

/** Losowy, czytelny ID np. U-K7M2QX */
export function generateParticipantId(): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // bez O/0/I/1
  let body = "";
  const bytes = new Uint8Array(6);
  crypto.getRandomValues(bytes);
  for (let i = 0; i < 6; i++) {
    body += alphabet[bytes[i]! % alphabet.length];
  }
  return `U-${body}`;
}

export function loadOrCreateParticipantId(): string {
  try {
    const existing = localStorage.getItem(STORAGE_KEY)?.trim();
    if (existing) return existing;
  } catch {
    /* ignore */
  }
  const id = generateParticipantId();
  saveParticipantId(id);
  return id;
}

export function saveParticipantId(id: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, id.trim());
  } catch {
    /* ignore */
  }
}
