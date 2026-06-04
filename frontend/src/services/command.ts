import { requestJson } from "@/services/http";
import type {
  CommandConnectPayload,
  CommandStatusResponse,
  CommandStudioResponse,
  UpdateCommandStudioPayload,
} from "@/types/command";

export function fetchCommandStatus(): Promise<CommandStatusResponse> {
  return requestJson<CommandStatusResponse>("/api/command/status");
}

export function fetchCommandStudio(): Promise<CommandStudioResponse> {
  return requestJson<CommandStudioResponse>("/api/command/studio");
}

export function connectCommand(payload: CommandConnectPayload): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>("/api/command/connect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function disconnectCommand(): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>("/api/command/disconnect", {
    method: "POST",
  });
}

export function saveCommandStudio(payload: UpdateCommandStudioPayload): Promise<CommandStudioResponse> {
  return requestJson<CommandStudioResponse>("/api/command/studio", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
