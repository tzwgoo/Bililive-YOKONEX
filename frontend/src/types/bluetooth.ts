export interface BluetoothStatusResponse {
  connected: boolean;
  message?: string;
  devices?: BluetoothDeviceResponse[];
  rules?: BluetoothRuleResponse[];
}

export interface BluetoothStudioResponse {
  ems_waveforms: BluetoothWaveform[];
  toy_waveforms: ToyWaveform[];
  rule_groups: BluetoothRuleGroup[];
  waveforms?: BluetoothWaveform[];
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
  toy_waveform_id?: string;
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

export interface BluetoothWaveformStep {
  duration_ms: number;
  channel_a: number;
  channel_b: number;
}

export interface BluetoothWaveform {
  id: string;
  name: string;
  builtin: boolean;
  editable: boolean;
  execution_mode?: string;
  loop_count?: number;
  steps: BluetoothWaveformStep[];
}

export interface ToyWaveformStep {
  duration_ms: number;
  motor_a: number;
  motor_b: number;
  motor_c: number;
}

export interface ToyWaveform {
  id: string;
  name: string;
  builtin: boolean;
  editable: boolean;
  device_family?: string;
  loop_count?: number;
  steps: ToyWaveformStep[];
}

export interface BluetoothStudioRule {
  id: string;
  event_type: string;
  rule_label: string;
  enabled: boolean;
  waveform_id: string;
  toy_waveform_id: string;
  waveform_name: string;
  cooldown_seconds?: number;
  filters?: Record<string, unknown>;
}

export interface BluetoothRuleGroup {
  group_id: string;
  group_label: string;
  rules: BluetoothStudioRule[];
}

export interface GuardWaveformOverride {
  waveform_id: string;
  toy_waveform_id: string;
}

export interface SaveBluetoothRulesPayload {
  rules: Array<{
    id: string;
    enabled: boolean;
    waveform_id: string;
    toy_waveform_id?: string;
    min_price: number | null;
    max_price: number | null;
    guard_waveforms: Record<string, GuardWaveformOverride> | null;
  }>;
}

export interface SaveBluetoothRulesResponse {
  success: boolean;
  updated_count: number;
  rule_groups: BluetoothRuleGroup[];
}

export interface BluetoothWaveformMutationResponse {
  success: boolean;
  waveform: BluetoothWaveform | ToyWaveform;
  ems_waveforms: BluetoothWaveform[];
  toy_waveforms: ToyWaveform[];
}

export interface UpdateBluetoothWaveformPayload {
  name: string;
  steps: BluetoothWaveformStep[] | ToyWaveformStep[];
}
