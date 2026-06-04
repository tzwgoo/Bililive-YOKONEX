import { requestJson } from "@/services/http";
import type { BluetoothStatusResponse, BluetoothStudioResponse } from "@/types/bluetooth";

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
