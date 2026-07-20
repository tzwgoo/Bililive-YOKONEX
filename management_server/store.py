from __future__ import annotations

import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import time
import uuid
from typing import Any


class ManagementStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    client_id TEXT PRIMARY KEY,
                    client_name TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    platform TEXT NOT NULL DEFAULT '',
                    user_id TEXT NOT NULL DEFAULT '',
                    command_connected INTEGER NOT NULL DEFAULT 0,
                    command_ids_json TEXT NOT NULL DEFAULT '[]',
                    waveform_revision TEXT NOT NULL DEFAULT '',
                    last_seen INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS devices (
                    client_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    device_type TEXT NOT NULL DEFAULT '',
                    protocol TEXT NOT NULL DEFAULT '',
                    connected INTEGER NOT NULL DEFAULT 0,
                    battery_level INTEGER,
                    active_waveform_id TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (client_id, device_id)
                );
                CREATE TABLE IF NOT EXISTS waveforms (
                    client_id TEXT NOT NULL,
                    waveform_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    waveform_type TEXT NOT NULL,
                    device_family TEXT NOT NULL,
                    builtin INTEGER NOT NULL DEFAULT 0,
                    editable INTEGER NOT NULL DEFAULT 0,
                    version_hash TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (client_id, waveform_id)
                );
                CREATE TABLE IF NOT EXISTS commands (
                    request_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    args_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    success INTEGER,
                    message TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL,
                    finished_at INTEGER
                );
                CREATE INDEX IF NOT EXISTS idx_commands_client_created
                    ON commands(client_id, created_at DESC);
                """
            )

    def enroll_client(self, *, client_name: str, platform: str) -> tuple[str, str]:
        client_id = uuid.uuid4().hex
        device_token = secrets.token_urlsafe(32)
        now = int(time.time())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO clients (
                    client_id, client_name, token_hash, platform, last_seen, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (client_id, client_name or client_id[:8], _hash_token(device_token), platform, now, now),
            )
        return client_id, device_token

    def authenticate_client(self, client_id: str, device_token: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT token_hash, revoked FROM clients WHERE client_id = ?",
                (client_id,),
            ).fetchone()
        return bool(row and not row["revoked"] and secrets.compare_digest(row["token_hash"], _hash_token(device_token)))

    def update_heartbeat(self, client_id: str, payload: dict[str, Any]) -> None:
        now = int(time.time())
        devices = payload.get("devices", []) if isinstance(payload.get("devices"), list) else []
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE clients
                SET client_name = ?, user_id = ?, command_connected = ?, last_seen = ?
                WHERE client_id = ?
                """,
                (
                    str(payload.get("client_name", "") or client_id[:8]),
                    str(payload.get("user_id", "") or ""),
                    int(bool(payload.get("command_connected"))),
                    now,
                    client_id,
                ),
            )
            connection.execute("UPDATE devices SET connected = 0 WHERE client_id = ?", (client_id,))
            for device in devices:
                connection.execute(
                    """
                    INSERT INTO devices (
                        client_id, device_id, name, device_type, protocol, connected,
                        battery_level, active_waveform_id, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(client_id, device_id) DO UPDATE SET
                        name = excluded.name,
                        device_type = excluded.device_type,
                        protocol = excluded.protocol,
                        connected = excluded.connected,
                        battery_level = excluded.battery_level,
                        active_waveform_id = excluded.active_waveform_id,
                        updated_at = excluded.updated_at
                    """,
                    (
                        client_id,
                        str(device.get("device_id", "") or ""),
                        str(device.get("name", "") or ""),
                        str(device.get("device_type", "") or ""),
                        str(device.get("protocol", "") or ""),
                        int(bool(device.get("connected"))),
                        device.get("battery_level"),
                        str(device.get("active_waveform_id", "") or ""),
                        now,
                    ),
                )

    def sync_capabilities(self, client_id: str, payload: dict[str, Any]) -> None:
        now = int(time.time())
        waveforms = payload.get("waveforms", []) if isinstance(payload.get("waveforms"), list) else []
        command_ids = payload.get("command_ids", []) if isinstance(payload.get("command_ids"), list) else []
        with self._connect() as connection:
            connection.execute(
                "UPDATE clients SET command_ids_json = ?, waveform_revision = ? WHERE client_id = ?",
                (
                    json.dumps(command_ids, ensure_ascii=False),
                    str(payload.get("waveform_revision", "") or ""),
                    client_id,
                ),
            )
            connection.execute("UPDATE waveforms SET active = 0 WHERE client_id = ?", (client_id,))
            for waveform in waveforms:
                connection.execute(
                    """
                    INSERT INTO waveforms (
                        client_id, waveform_id, name, waveform_type, device_family,
                        builtin, editable, version_hash, active, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(client_id, waveform_id) DO UPDATE SET
                        name = excluded.name,
                        waveform_type = excluded.waveform_type,
                        device_family = excluded.device_family,
                        builtin = excluded.builtin,
                        editable = excluded.editable,
                        version_hash = excluded.version_hash,
                        active = 1,
                        updated_at = excluded.updated_at
                    """,
                    (
                        client_id,
                        str(waveform.get("waveform_id", "") or ""),
                        str(waveform.get("name", "") or ""),
                        str(waveform.get("waveform_type", "") or ""),
                        str(waveform.get("device_family", "") or ""),
                        int(bool(waveform.get("builtin"))),
                        int(bool(waveform.get("editable"))),
                        str(waveform.get("version_hash", "") or ""),
                        now,
                    ),
                )

    def list_clients(self, online_client_ids: set[str]) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT c.*,
                       COUNT(DISTINCT CASE WHEN d.connected = 1 THEN d.device_id END) AS connected_devices,
                       COUNT(DISTINCT CASE WHEN w.active = 1 THEN w.waveform_id END) AS waveform_count
                FROM clients c
                LEFT JOIN devices d ON d.client_id = c.client_id
                LEFT JOIN waveforms w ON w.client_id = c.client_id
                WHERE c.revoked = 0
                GROUP BY c.client_id
                ORDER BY c.last_seen DESC
                """
            ).fetchall()
        return [
            {
                **dict(row),
                "online": row["client_id"] in online_client_ids,
                "command_connected": bool(row["command_connected"]),
            }
            for row in rows
        ]

    def get_client(self, client_id: str, *, online: bool) -> dict[str, Any] | None:
        with self._connect() as connection:
            client = connection.execute(
                "SELECT * FROM clients WHERE client_id = ? AND revoked = 0",
                (client_id,),
            ).fetchone()
            if client is None:
                return None
            devices = connection.execute(
                "SELECT * FROM devices WHERE client_id = ? ORDER BY connected DESC, name",
                (client_id,),
            ).fetchall()
            waveforms = connection.execute(
                "SELECT * FROM waveforms WHERE client_id = ? AND active = 1 ORDER BY waveform_type, name",
                (client_id,),
            ).fetchall()
            commands = connection.execute(
                "SELECT * FROM commands WHERE client_id = ? ORDER BY created_at DESC LIMIT 30",
                (client_id,),
            ).fetchall()
        return {
            **dict(client),
            "online": online,
            "command_connected": bool(client["command_connected"]),
            "command_ids": json.loads(client["command_ids_json"] or "[]"),
            "devices": [{**dict(item), "connected": bool(item["connected"])} for item in devices],
            "waveforms": [
                {**dict(item), "builtin": bool(item["builtin"]), "editable": bool(item["editable"])}
                for item in waveforms
            ],
            "commands": [
                {
                    **dict(item),
                    "success": None if item["success"] is None else bool(item["success"]),
                    "args": json.loads(item["args_json"] or "{}"),
                }
                for item in commands
            ],
        }

    def get_waveform(self, client_id: str, waveform_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM waveforms WHERE client_id = ? AND waveform_id = ? AND active = 1",
                (client_id, waveform_id),
            ).fetchone()
        return None if row is None else dict(row)

    def get_device(self, client_id: str, device_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM devices WHERE client_id = ? AND device_id = ?",
                (client_id, device_id),
            ).fetchone()
        return None if row is None else {**dict(row), "connected": bool(row["connected"])}

    def create_command(self, request_id: str, client_id: str, action: str, args: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO commands (request_id, client_id, action, args_json, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
                """,
                (request_id, client_id, action, json.dumps(args, ensure_ascii=False), int(time.time())),
            )

    def finish_command(self, request_id: str, *, success: bool, message: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE commands
                SET status = 'finished', success = ?, message = ?, finished_at = ?
                WHERE request_id = ?
                """,
                (int(success), message, int(time.time()), request_id),
            )

    def fail_command(self, request_id: str, message: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE commands
                SET status = 'failed', success = 0, message = ?, finished_at = ?
                WHERE request_id = ?
                """,
                (message, int(time.time()), request_id),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _hash_token(token: str) -> str:
    # 设备令牌本身具有足够随机度，数据库只保存不可逆摘要。
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
