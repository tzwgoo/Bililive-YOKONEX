export interface CommandStatusResponse {
  status: string;
  message?: string;
  uid?: string;
  user_id?: string;
  last_login_at?: number;
  can_connect?: boolean;
  can_disconnect?: boolean;
}

export interface CommandStatusModel {
  status: string;
  message: string;
  uid: string;
  userId: string;
  lastLoginAt: number;
  canConnect: boolean;
  canDisconnect: boolean;
}

export interface CommandStudioResponse {
  rules: CommandStudioRule[];
  like_command_id: string;
  interact_command_id: string;
  danmaku_command_ids: Record<string, string>;
  command_slots: string[];
  event_types?: CommandEventTypeOption[];
  danmaku_event_types?: CommandDanmakuEventTypeOption[];
}

export interface CommandConnectPayload {
  ws_url: string;
  uid: string;
  token: string;
}

export interface CommandStudioRule {
  id: string;
  enabled: boolean;
  event_type: string;
  min_price: number;
  max_price: number | null;
  command_slot: string;
}

export interface CommandEventTypeOption {
  value: string;
  label: string;
}

export interface CommandDanmakuEventTypeOption {
  value: string;
  label: string;
  guard_level: number;
}

export interface UpdateCommandStudioPayload {
  rules: CommandStudioRule[];
  like_rules: Array<Record<string, unknown>>;
  danmaku_slot_rules: Array<Record<string, unknown>>;
}
