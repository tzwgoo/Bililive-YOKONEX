import { requestJson } from "@/services/http";
import type { SessionStartPayload, SessionStatusResponse } from "@/types/session";

export function fetchSessionStatus(): Promise<SessionStatusResponse> {
  return requestJson<SessionStatusResponse>("/api/status");
}

export function startSession(payload: SessionStartPayload): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>("/api/session/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function stopSession(): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>("/api/session/stop", {
    method: "POST",
  });
}
