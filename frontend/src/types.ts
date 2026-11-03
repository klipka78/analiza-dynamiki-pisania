export type KeystrokeEvent = {
  t: number;
  type: "down" | "up";
  code: string;
  key: string;
  keyCode: number;
  shift: boolean;
  ctrl: boolean;
  alt: boolean;
};

export type SessionPayload = {
  participantId: string;
  taskId: string;
  referenceText: string;
  typedText: string;
  keyboardLayout: string;
  language: string;
  userAgent: string;
  environment: string;
  keyboardType: string;
  dominantHand: string;
  fatigue: number;
  durationMs: number;
  events: KeystrokeEvent[];
};

export type SessionSummary = {
  id: number;
  session_uid: string;
  participant_id: string;
  task_id: string;
  event_count: number;
  created_at: string;
  typed_len: number;
  reference_len: number;
  environment?: string;
  keyboard_type?: string;
  dominant_hand?: string;
  fatigue?: number;
  duration_ms?: number;
};
