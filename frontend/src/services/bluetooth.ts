import { requestJson } from "@/services/http";
import type {
  BluetoothStatusResponse,
  BluetoothStudioResponse,
  BluetoothWaveformMutationResponse,
  SaveBluetoothRulesPayload,
  SaveBluetoothRulesResponse,
  UpdateBluetoothWaveformPayload,
} from "@/types/bluetooth";

export function fetchBluetoothStatus(): Promise<BluetoothStatusResponse> {
  return requestJson<BluetoothStatusResponse>("/api/bluetooth/status");
}

export function fetchBluetoothStudio(): Promise<BluetoothStudioResponse> {
  return requestJson<BluetoothStudioResponse>("/api/bluetooth/studio");
}

export function scanBluetoothDevices(): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>("/api/bluetooth/scan", {
    method: "POST",
  });
}

export function connectBluetoothDevice(deviceId: string): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>("/api/bluetooth/connect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ device_id: deviceId }),
  });
}

export function disconnectBluetoothDevice(): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>("/api/bluetooth/disconnect", {
    method: "POST",
  });
}

export function saveBluetoothRules(payload: SaveBluetoothRulesPayload): Promise<SaveBluetoothRulesResponse> {
  return requestJson<SaveBluetoothRulesResponse>("/api/bluetooth/rules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function createBluetoothWaveform(name: string): Promise<BluetoothWaveformMutationResponse> {
  return requestJson<BluetoothWaveformMutationResponse>("/api/bluetooth/waveforms", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function duplicateBluetoothWaveform(waveformId: string, name: string): Promise<BluetoothWaveformMutationResponse> {
  return requestJson<BluetoothWaveformMutationResponse>(`/api/bluetooth/waveforms/${encodeURIComponent(waveformId)}/duplicate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function updateBluetoothWaveform(
  waveformId: string,
  payload: UpdateBluetoothWaveformPayload,
): Promise<BluetoothWaveformMutationResponse> {
  return requestJson<BluetoothWaveformMutationResponse>(`/api/bluetooth/waveforms/${encodeURIComponent(waveformId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function deleteBluetoothWaveform(waveformId: string): Promise<{ success: boolean; deleted_waveform_id: string; waveforms: BluetoothStudioResponse["waveforms"] }> {
  return requestJson<{ success: boolean; deleted_waveform_id: string; waveforms: BluetoothStudioResponse["waveforms"] }>(
    `/api/bluetooth/waveforms/${encodeURIComponent(waveformId)}`,
    {
      method: "DELETE",
    },
  );
}
