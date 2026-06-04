export interface SessionStatusResponse {
  status: string;
  room_id?: number | string;
  message?: string;
  anchor_name?: string;
  last_event_at?: number;
  can_start?: boolean;
  can_stop?: boolean;
  mode?: string;
  connection_mode?: string;
  output_mode?: string;
  trigger_mode?: string;
  like_multiple?: number;
  danmaku_enabled?: boolean;
  danmaku_keywords?: string;
  danmaku_cooldown_seconds?: number;
  danmaku_user_limit_window_seconds?: number;
  danmaku_user_limit_max_triggers?: number;
  danmaku_min_guard_level?: number;
}

export interface SessionStatusModel {
  status: string;
  roomId: string;
  message: string;
  anchorName: string;
  lastEventAt: number;
  canStart: boolean;
  canStop: boolean;
  mode: string;
  connectionMode: string;
  triggerMode: string;
  likeMultiple: number;
  danmakuEnabled: boolean;
  danmakuKeywords: string;
  danmakuCooldownSeconds: number;
  danmakuUserLimitWindowSeconds: number;
  danmakuUserLimitMaxTriggers: number;
  danmakuMinGuardLevel: number;
}

export interface SessionStartPayload {
  mode: string;
  value: string;
  connection_mode: string;
  output_mode: string;
  trigger_mode: string;
  like_multiple: number;
  danmaku_enabled: boolean;
  danmaku_keywords: string;
  danmaku_cooldown_seconds: number;
  danmaku_user_limit_window_seconds: number;
  danmaku_user_limit_max_triggers: number;
  danmaku_min_guard_level: number;
}
