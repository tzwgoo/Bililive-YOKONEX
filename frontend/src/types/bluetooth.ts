export interface BluetoothStatusResponse {
  connected: boolean;
  message?: string;
  devices?: BluetoothDeviceResponse[];
  rules?: BluetoothRuleResponse[];
}

export interface BluetoothStudioResponse {
  waveforms: Array<Record<string, unknown>>;
  rule_groups: Array<Record<string, unknown>>;
}

export interface BluetoothDeviceResponse {
  device_id?: string;
  name?: string;
  device_type?: string;
  protocol?: string;
  rssi?: number;
  connected?: boolean;
}

export interface BluetoothRuleResponse {
  id?: string;
  enabled?: boolean;
  waveform_id?: string;
  waveform_name?: string;
  rule_label?: string;
  event_label?: string;
  event_type?: string;
}

export interface BluetoothDeviceModel {
  deviceId: string;
  name: string;
  deviceType: string;
  protocol: string;
  rssi: number;
  connected: boolean;
}

export interface BluetoothRuleModel {
  id: string;
  enabled: boolean;
  waveformId: string;
  waveformName: string;
  ruleLabel: string;
  eventType: string;
}

export interface BluetoothStatusModel {
  connected: boolean;
  message: string;
  devices: BluetoothDeviceModel[];
  rules: BluetoothRuleModel[];
}
