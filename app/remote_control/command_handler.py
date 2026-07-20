from __future__ import annotations

from typing import Any

from app.remote_control.protocol import ALLOWED_ACTIONS, COMMAND_IDS


class RemoteCommandHandler:
    def __init__(self, *, command_session: Any, bluetooth_service: Any) -> None:
        self.command_session = command_session
        self.bluetooth_service = bluetooth_service

    async def execute(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """只执行明确开放的业务命令，绝不接受任意方法名或脚本。"""
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"不支持的远程操作: {action}")
        if action == "command.send":
            return await self._send_command(args)
        if action == "waveform.play":
            return await self._play_waveform(args)
        if action == "waveform.stop":
            return await self.bluetooth_service.stop_waveform(
                str(args.get("device_id", "") or "").strip() or None
            )
        if action == "output.fixed":
            return await self._trigger_fixed_output(args)
        return await self._disconnect_device(args)

    async def _send_command(self, args: dict[str, Any]) -> dict[str, Any]:
        command_id = str(args.get("command_id", "") or "").strip()
        if command_id not in COMMAND_IDS:
            raise ValueError(f"不支持的 commandId: {command_id}")
        return await self.command_session.send_command(command_id=command_id)

    async def _play_waveform(self, args: dict[str, Any]) -> dict[str, Any]:
        waveform_id = str(args.get("waveform_id", "") or "").strip()
        device_id = str(args.get("device_id", "") or "").strip()
        expected_hash = str(args.get("version_hash", "") or "").strip()
        if not waveform_id or not device_id or not expected_hash:
            raise ValueError("波形、设备和版本哈希不能为空")

        waveform = self.bluetooth_service.get_remote_waveform_summary(waveform_id)
        if waveform["version_hash"] != expected_hash:
            raise ValueError("波形已经发生变化，请刷新后重试")

        devices = self.bluetooth_service.get_status_payload().get("devices", [])
        device = next(
            (item for item in devices if item.get("device_id") == device_id and item.get("connected")),
            None,
        )
        if device is None:
            raise ValueError("目标设备未连接")
        self._validate_waveform_device(waveform, device)
        return await self.bluetooth_service.trigger_waveform(
            event_type="remote_control",
            waveform_id=waveform_id,
            device_id=device_id,
        )

    async def _disconnect_device(self, args: dict[str, Any]) -> dict[str, Any]:
        device_id = str(args.get("device_id", "") or "").strip()
        if not device_id:
            raise ValueError("设备 ID 不能为空")
        # 先停止正在运行的波形，确保运行时发送停止包后再断开蓝牙。
        await self.bluetooth_service.stop_waveform(device_id)
        await self.bluetooth_service.disconnect(device_id)
        devices = self.bluetooth_service.get_status_payload().get("devices", [])
        still_connected = any(
            item.get("device_id") == device_id and item.get("connected")
            for item in devices
        )
        return {
            "success": not still_connected,
            "message": "设备已断开" if not still_connected else "设备断开失败",
            "device_id": device_id,
        }

    async def _trigger_fixed_output(self, args: dict[str, Any]) -> dict[str, Any]:
        device_id = str(args.get("device_id", "") or "").strip()
        try:
            strength = int(args.get("strength", 0))
            duration_seconds = int(args.get("duration_seconds", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("强度和时长必须是整数") from exc
        if not device_id:
            raise ValueError("设备 ID 不能为空")
        if not 1 <= duration_seconds <= 60:
            raise ValueError("固定输出时长只能是 1 到 60 秒")

        devices = self.bluetooth_service.get_status_payload().get("devices", [])
        device = next(
            (item for item in devices if item.get("device_id") == device_id and item.get("connected")),
            None,
        )
        if device is None:
            raise ValueError("目标设备未连接")
        protocol = str(device.get("protocol", ""))
        if "gcq" in protocol:
            raise ValueError("灌肠机不支持单一固定强度控制")
        max_strength = 20 if str(device.get("device_type", "")) == "toy" else 180
        if not 1 <= strength <= max_strength:
            raise ValueError(f"当前设备强度只能是 1 到 {max_strength}")
        return await self.bluetooth_service.trigger_fixed_output(
            device_id=device_id,
            strength=strength,
            duration_seconds=duration_seconds,
        )

    @staticmethod
    def _validate_waveform_device(waveform: dict[str, Any], device: dict[str, Any]) -> None:
        waveform_type = str(waveform.get("waveform_type", ""))
        device_type = str(device.get("device_type", ""))
        if waveform_type == "toy" and device_type != "toy":
            raise ValueError("Toy 波形不能发送到 EMS 设备")
        if waveform_type == "ems" and device_type == "toy":
            raise ValueError("EMS 波形不能发送到 Toy 设备")

        family = str(waveform.get("device_family", ""))
        protocol = str(device.get("protocol", ""))
        if family == "gcq" and "gcq" not in protocol:
            raise ValueError("灌肠机波形与目标设备不兼容")
        if family == "toy" and "gcq" in protocol:
            raise ValueError("普通 Toy 波形与灌肠机设备不兼容")
