from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any

from app.bluetooth.models import BluetoothConnectionStatus
from app.bluetooth.models import BluetoothDevice
from app.bluetooth.models import EmsWaveform
from app.bluetooth.models import EmsWaveformStep
from app.bluetooth.models import ToyWaveform
from app.bluetooth.models import ToyWaveformStep

try:
    from bleak import BleakClient
    from bleak import BleakScanner
except ImportError:  # pragma: no cover - exercised through runtime fallback
    BleakClient = None
    BleakScanner = None


EMS_SERVICE_UUID = "0000ff30-0000-1000-8000-00805f9b34fb"
EMS_WRITE_CHAR_UUID = "0000ff31-0000-1000-8000-00805f9b34fb"
EMS_NOTIFY_CHAR_UUID = "0000ff32-0000-1000-8000-00805f9b34fb"

TOY_SERVICE_UUID = "0000ff40-0000-1000-8000-00805f9b34fb"
TOY_WRITE_CHAR_UUID = "0000ff41-0000-1000-8000-00805f9b34fb"
TOY_NOTIFY_CHAR_UUID = "0000ff42-0000-1000-8000-00805f9b34fb"

TOY_NAME_PREFIXES = ("YCY-FJB", "YCY-TDD")
TOY_MOTOR_ALL = 0x07

LOGGER = logging.getLogger("bili_live.bluetooth.runtime")


class BleakBluetoothRuntime:
    backend_name = "bleak"

    def __init__(
        self,
        *,
        scan_timeout_seconds: int,
        connect_timeout_seconds: float = 20,
        auto_reconnect: bool = False,
        scanner_discover: Callable[..., Awaitable[Any]] | None = None,
        client_factory: Callable[..., Any] | None = None,
        sleep_func: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        if scanner_discover is None:
            if BleakScanner is None:
                raise RuntimeError("未安装 bleak，无法启用真实蓝牙运行时")
            scanner_discover = BleakScanner.discover
        if client_factory is None:
            if BleakClient is None:
                raise RuntimeError("未安装 bleak，无法启用真实蓝牙运行时")
            client_factory = BleakClient
        self._scan_timeout_seconds = scan_timeout_seconds
        self._connect_timeout_seconds = max(0.01, float(connect_timeout_seconds))
        self._auto_reconnect = bool(auto_reconnect)
        self._scanner_discover = scanner_discover
        self._client_factory = client_factory
        self._sleep = sleep_func or asyncio.sleep
        self._devices: list[BluetoothDevice] = []
        self._ble_devices: dict[str, Any] = {}
        self._client: Any | None = None
        self._connected_device_id = ""
        self._manual_disconnect_requested = False
        self._reconnect_task: asyncio.Task | None = None
        self._battery_level: int | None = None
        self._status_message = "未连接"
        self._overlay_payload = {
            "connected": False,
            "device_name": "",
            "device_type": "",
            "waveform_name": "",
            "battery_level": None,
            "channel_a": 0,
            "channel_b": 0,
            "motor_a": 0,
            "motor_b": 0,
            "motor_c": 0,
            "step_index": 0,
            "step_count": 0,
            "updated_at": 0.0,
            "history": [],
            "revision": 0,
        }

    async def scan(self) -> list[BluetoothDevice]:
        discovered = await self._scanner_discover(
            timeout=self._scan_timeout_seconds,
            return_adv=True,
        )
        devices: list[BluetoothDevice] = []
        ble_devices: dict[str, Any] = {}
        if isinstance(discovered, dict):
            values = discovered.values()
        else:
            values = ((item, SimpleNamespace(service_uuids=[])) for item in discovered)
        for ble_device, advertisement in values:
            mapped = classify_device(ble_device=ble_device, advertisement=advertisement)
            if mapped is None:
                continue
            devices.append(mapped)
            ble_devices[mapped.device_id] = ble_device
        self._devices = devices
        self._ble_devices = ble_devices
        self._sync_connected_flags()
        return list(self._devices)

    async def connect(self, device_id: str) -> BluetoothConnectionStatus:
        ble_device = self._ble_devices.get(device_id)
        device = next((item for item in self._devices if item.device_id == device_id), None)
        if ble_device is None or device is None:
            raise ValueError("未找到指定蓝牙设备")
        if self._client is not None and getattr(self._client, "is_connected", False):
            await self.disconnect()
        if self._reconnect_task is not None and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            self._reconnect_task = None
        client = self._client_factory(
            ble_device,
            disconnected_callback=self._handle_disconnect,
        )
        await asyncio.wait_for(client.connect(), timeout=self._connect_timeout_seconds)
        self._client = client
        self._connected_device_id = device_id if getattr(client, "is_connected", False) else ""
        self._sync_connected_flags()
        if not self._connected_device_id:
            raise RuntimeError("蓝牙设备连接失败")
        await self._initialize_device_telemetry(device)
        self._status_message = f"已连接 {device.name}"
        self._set_overlay_payload(
            connected=True,
            device_name=device.name,
            device_type=device.device_type,
            battery_level=self._battery_level,
        )
        return BluetoothConnectionStatus(
            connected=True,
            device=device,
            battery_level=self._battery_level,
            message=self._status_message,
        )

    async def disconnect(self) -> BluetoothConnectionStatus:
        client = self._client
        device = next((item for item in self._devices if item.connected), None)
        self._manual_disconnect_requested = True
        if self._reconnect_task is not None and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            self._reconnect_task = None
        self._client = None
        self._connected_device_id = ""
        self._battery_level = None
        if client is not None and getattr(client, "is_connected", False):
            stop_notify = getattr(client, "stop_notify", None)
            if callable(stop_notify):
                notify_uuid = TOY_NOTIFY_CHAR_UUID if (device and device.device_type == "toy") else EMS_NOTIFY_CHAR_UUID
                try:
                    await stop_notify(notify_uuid)
                except Exception:
                    LOGGER.debug("停止蓝牙通知失败", exc_info=True)
            await client.disconnect()
        self._manual_disconnect_requested = False
        self._sync_connected_flags()
        self._status_message = "已断开蓝牙设备"
        self._set_overlay_payload(
            connected=False,
            device_name="",
            device_type="",
            waveform_name="",
            battery_level=None,
            channel_a=0,
            channel_b=0,
            motor_a=0,
            motor_b=0,
            motor_c=0,
            step_index=0,
            step_count=0,
            history=[],
        )
        return BluetoothConnectionStatus(
            connected=False,
            device=None,
            battery_level=None,
            message=self._status_message,
        )

    def get_status(self) -> BluetoothConnectionStatus:
        device = next((item for item in self._devices if item.connected), None)
        return BluetoothConnectionStatus(
            connected=device is not None,
            device=device,
            battery_level=self._battery_level if device is not None else None,
            message=self._status_message if self._status_message else (f"已连接 {device.name}" if device is not None else "未连接"),
        )

    def get_devices(self) -> list[BluetoothDevice]:
        return list(self._devices)

    def get_overlay_payload(self) -> dict:
        return {
            **self._overlay_payload,
            "history": list(self._overlay_payload["history"]),
        }

    async def play_waveform(self, waveform: EmsWaveform | ToyWaveform) -> None:
        if self._client is None or not getattr(self._client, "is_connected", False):
            raise RuntimeError("当前没有已连接的蓝牙设备")
        device = next((item for item in self._devices if item.connected), None)
        if device is None:
            raise RuntimeError("未找到当前连接设备")
        is_toy_device = device.device_type == "toy"
        write_uuid = TOY_WRITE_CHAR_UUID if is_toy_device else EMS_WRITE_CHAR_UUID
        history = list(self._overlay_payload["history"])
        try:
            if is_toy_device:
                for index, step in enumerate(waveform.steps, start=1):
                    if isinstance(step, ToyWaveformStep):
                        toy_step = step
                    else:
                        toy_step = _ems_step_to_toy(step)
                    packet = create_toy_speed_packet(toy_step)
                    history.append(
                        {
                            "motor_a": toy_step.motor_a,
                            "motor_b": toy_step.motor_b,
                            "motor_c": toy_step.motor_c,
                        }
                    )
                    history = history[-90:]
                    self._set_overlay_payload(
                        connected=True,
                        device_name=device.name,
                        device_type=device.device_type,
                        waveform_name=waveform.name,
                        motor_a=toy_step.motor_a,
                        motor_b=toy_step.motor_b,
                        motor_c=toy_step.motor_c,
                        step_index=index,
                        step_count=len(waveform.steps),
                        history=history,
                    )
                    await self._client.write_gatt_char(write_uuid, packet, response=False)
                    await self._sleep(max(getattr(step, "duration_ms", 200), 0) / 1000)
            else:
                packets = create_waveform_packets(waveform=waveform, protocol=device.protocol)
                for index, ((packet, duration_seconds), step) in enumerate(zip(packets, waveform.steps, strict=False), start=1):
                    history.append(
                        {
                            "channel_a": getattr(step, "channel_a", 0),
                            "channel_b": getattr(step, "channel_b", 0),
                        }
                    )
                    history = history[-90:]
                    self._set_overlay_payload(
                        connected=True,
                        device_name=device.name,
                        device_type=device.device_type,
                        waveform_name=waveform.name,
                        channel_a=getattr(step, "channel_a", 0),
                        channel_b=getattr(step, "channel_b", 0),
                        step_index=index,
                        step_count=len(waveform.steps),
                        history=history,
                    )
                    await self._client.write_gatt_char(write_uuid, packet, response=False)
                    await self._sleep(duration_seconds)
        finally:
            if is_toy_device:
                stop_packet = create_toy_stop_packet()
            else:
                stop_packet = create_stop_packet(protocol=device.protocol)
            await self._client.write_gatt_char(write_uuid, stop_packet, response=False)
            if is_toy_device:
                self._set_overlay_payload(
                    connected=True,
                    device_name=device.name,
                    device_type=device.device_type,
                    waveform_name="",
                    motor_a=0,
                    motor_b=0,
                    motor_c=0,
                    step_index=0,
                    step_count=0,
                    history=[*history, {"motor_a": 0, "motor_b": 0, "motor_c": 0}][-90:],
                )
            else:
                self._set_overlay_payload(
                    connected=True,
                    device_name=device.name,
                    device_type=device.device_type,
                    waveform_name="",
                    channel_a=0,
                    channel_b=0,
                    step_index=0,
                    step_count=0,
                    history=[*history, {"channel_a": 0, "channel_b": 0}][-90:],
                )

    def _handle_disconnect(self, _client: Any) -> None:
        previous_device_id = self._connected_device_id
        previous_device_name = next(
            (item.name for item in self._devices if item.device_id == previous_device_id),
            "",
        )
        self._connected_device_id = ""
        self._client = None
        self._battery_level = None
        self._sync_connected_flags()
        if self._manual_disconnect_requested:
            LOGGER.info("蓝牙设备已主动断开 device_id=%s name=%s", previous_device_id, previous_device_name)
            return
        self._status_message = f"蓝牙设备已断开: {previous_device_name or previous_device_id or '未知设备'}"
        LOGGER.warning(
            "蓝牙设备连接断开 device_id=%s name=%s auto_reconnect=%s",
            previous_device_id,
            previous_device_name,
            self._auto_reconnect,
        )
        self._set_overlay_payload(
            connected=False,
            device_name="",
            device_type="",
            waveform_name="",
            battery_level=None,
            channel_a=0,
            channel_b=0,
            motor_a=0,
            motor_b=0,
            motor_c=0,
            step_index=0,
            step_count=0,
            history=[],
        )
        if self._auto_reconnect and previous_device_id and (self._reconnect_task is None or self._reconnect_task.done()):
            self._status_message = f"蓝牙设备已断开，正在尝试重连: {previous_device_name or previous_device_id}"
            self._reconnect_task = asyncio.create_task(
                self._attempt_reconnect(previous_device_id, previous_device_name)
            )

    def _sync_connected_flags(self) -> None:
        for item in self._devices:
            item.connected = item.device_id == self._connected_device_id

    async def _attempt_reconnect(self, device_id: str, device_name: str) -> None:
        try:
            await self._sleep(1.5)
            ble_device = self._ble_devices.get(device_id)
            device = next((item for item in self._devices if item.device_id == device_id), None)
            if ble_device is None or device is None:
                self._status_message = f"蓝牙设备已断开，且无法找到设备进行重连: {device_name or device_id}"
                LOGGER.warning("蓝牙自动重连失败，设备已不存在 device_id=%s name=%s", device_id, device_name)
                return
            client = self._client_factory(
                ble_device,
                disconnected_callback=self._handle_disconnect,
            )
            await asyncio.wait_for(client.connect(), timeout=self._connect_timeout_seconds)
            self._client = client
            self._connected_device_id = device_id if getattr(client, "is_connected", False) else ""
            self._sync_connected_flags()
            if not self._connected_device_id:
                raise RuntimeError("蓝牙自动重连后状态仍未连接")
            await self._initialize_device_telemetry(device)
            self._status_message = f"蓝牙已自动重连 {device.name}"
            LOGGER.info("蓝牙自动重连成功 device_id=%s name=%s", device_id, device.name)
            self._set_overlay_payload(
                connected=True,
                device_name=device.name,
                device_type=device.device_type,
                battery_level=self._battery_level,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._status_message = f"蓝牙自动重连失败: {exc}"
            LOGGER.warning("蓝牙自动重连失败 device_id=%s name=%s error=%s", device_id, device_name, exc)
        finally:
            self._reconnect_task = None

    def _set_overlay_payload(self, **updates) -> None:
        self._overlay_payload = {
            **self._overlay_payload,
            **updates,
            "updated_at": time.time(),
            "revision": int(self._overlay_payload.get("revision", 0)) + 1,
        }

    async def _initialize_device_telemetry(self, device: BluetoothDevice) -> None:
        self._battery_level = None
        client = self._client
        if client is None or not getattr(client, "is_connected", False):
            return
        if device.device_type == "toy":
            start_notify = getattr(client, "start_notify", None)
            if callable(start_notify):
                await start_notify(TOY_NOTIFY_CHAR_UUID, self._handle_toy_notify)
            await client.write_gatt_char(
                TOY_WRITE_CHAR_UUID,
                _build_toy_device_info_query(),
                response=False,
            )
            return
        # YYC-DJ v1 / v2 当前都走同一套 EMS 通知特征和电量查询包。
        if device.device_type != "ems":
            return
        start_notify = getattr(client, "start_notify", None)
        if not callable(start_notify):
            return
        await start_notify(EMS_NOTIFY_CHAR_UUID, self._handle_notify)
        await client.write_gatt_char(
            EMS_WRITE_CHAR_UUID,
            _build_ems_query_packet(0x04),
            response=False,
        )

    async def _handle_notify(self, _sender: Any, data: bytearray) -> None:
        battery_level = _try_parse_ems_battery_level(bytes(data))
        if battery_level is None:
            return
        self._battery_level = battery_level
        if self._connected_device_id:
            device = next((item for item in self._devices if item.device_id == self._connected_device_id), None)
            self._set_overlay_payload(
                connected=True,
                device_name="" if device is None else device.name,
                battery_level=battery_level,
            )

    async def _handle_toy_notify(self, _sender: Any, data: bytearray) -> None:
        parsed = _try_parse_toy_notify(bytes(data))
        if parsed is None:
            return
        if parsed.get("type") == "battery":
            self._battery_level = parsed["level"]
        if self._connected_device_id:
            device = next((item for item in self._devices if item.device_id == self._connected_device_id), None)
            self._set_overlay_payload(
                connected=True,
                device_name="" if device is None else device.name,
                battery_level=self._battery_level,
            )


def classify_ems_device(*, ble_device: Any, advertisement: Any) -> BluetoothDevice | None:
    """向后兼容别名，委托给 classify_device。"""
    return classify_device(ble_device=ble_device, advertisement=advertisement)


def classify_device(*, ble_device: Any, advertisement: Any) -> BluetoothDevice | None:
    """分类蓝牙广播设备，返回 BluetoothDevice 或 None。"""
    service_uuids = _normalize_service_uuids(getattr(advertisement, "service_uuids", []))
    name = (
        getattr(advertisement, "local_name", None)
        or getattr(ble_device, "name", None)
        or getattr(ble_device, "address", "")
    )
    name_upper = str(name).upper()

    # Toy 设备优先匹配 (FF40 / YCY-FJB / YCY-TDD)
    if TOY_SERVICE_UUID in service_uuids or any(name_upper.startswith(prefix) for prefix in TOY_NAME_PREFIXES):
        return BluetoothDevice(
            device_id=str(getattr(ble_device, "address", "")),
            name=str(name),
            device_type="toy",
            protocol="toy",
            rssi=int(getattr(ble_device, "rssi", getattr(advertisement, "rssi", -60)) or -60),
            connected=False,
        )

    # EMS 设备 (FF30 / YYC-DJ)
    if EMS_SERVICE_UUID not in service_uuids and not name_upper.startswith("YYC-DJ"):
        return None
    protocol = "ems_v2"
    if name_upper.startswith("YYC-DJ-V2"):
        protocol = "ems_v2"
    elif name_upper.startswith("YYC-DJ"):
        protocol = "ems_v1"
    return BluetoothDevice(
        device_id=str(getattr(ble_device, "address", "")),
        name=str(name),
        device_type="ems",
        protocol=protocol,
        rssi=int(getattr(ble_device, "rssi", getattr(advertisement, "rssi", -60)) or -60),
        connected=False,
    )


def create_waveform_packets(*, waveform: EmsWaveform, protocol: str) -> list[tuple[bytes, float]]:
    packets: list[tuple[bytes, float]] = []
    for step in waveform.steps:
        if protocol == "ems_v1":
            packet = _create_v1_packet(step)
        elif str(waveform.execution_mode).lower() == "realtime":
            packet = _create_v2_realtime_packet(step)
        else:
            packet = _create_v2_fixed_packet(step)
        packets.append((packet, max(step.duration_ms, 0) / 1000))
    return packets


def create_stop_packet(*, protocol: str) -> bytes:
    if protocol == "ems_v1":
        return _create_v1_stop_packet()
    return _create_v2_fixed_packet(
        EmsWaveformStep(duration_ms=0, channel_a=0, channel_b=0),
    )


def _create_v1_packet(step: EmsWaveformStep) -> bytes:
    channel = _resolve_v1_channel(step)
    enabled = 0x01 if channel != 0x00 else 0x00
    use_channel_b = channel == 0x02 or step.channel_b > step.channel_a
    strength = step.channel_b if use_channel_b else step.channel_a
    mode = step.channel_b_mode if use_channel_b else step.channel_a_mode
    frequency = step.channel_b_frequency if use_channel_b else step.channel_a_frequency
    pulse_width = step.channel_b_pulse_width if use_channel_b else step.channel_a_pulse_width
    bytes_list = [
        0x35,
        0x11,
        channel,
        enabled,
        _high(strength),
        _low(strength),
        mode,
        frequency if mode == 0x11 else 0x00,
        pulse_width if mode == 0x11 else 0x00,
    ]
    bytes_list.append(_compute_checksum(bytes_list))
    return bytes(bytes_list)


def _create_v2_fixed_packet(step: EmsWaveformStep) -> bytes:
    bytes_list = [
        0x35,
        0x11,
        0x01,
        _high(step.channel_a),
        _low(step.channel_a),
        step.channel_a_mode,
        _high(step.channel_b),
        _low(step.channel_b),
        step.channel_b_mode,
    ]
    bytes_list.append(_compute_checksum(bytes_list))
    return bytes(bytes_list)


def _create_v2_realtime_packet(step: EmsWaveformStep) -> bytes:
    bytes_list = [
        0x35,
        0x11,
        0x02,
        _high(step.channel_a),
        _low(step.channel_a),
        step.channel_a_frequency,
        step.channel_a_pulse_width,
        _high(step.channel_b),
        _low(step.channel_b),
        step.channel_b_frequency,
        step.channel_b_pulse_width,
    ]
    bytes_list.append(_compute_checksum(bytes_list))
    return bytes(bytes_list)


def _create_v1_stop_packet() -> bytes:
    bytes_list = [
        0x35,
        0x11,
        0x03,
        0x00,
        0x00,
        0x01,
        0x01,
        0x00,
        0x00,
    ]
    bytes_list.append(_compute_checksum(bytes_list))
    return bytes(bytes_list)


def _resolve_v1_channel(step: EmsWaveformStep) -> int:
    a_enabled = step.channel_a > 0
    b_enabled = step.channel_b > 0
    if a_enabled and b_enabled:
        return 0x03
    if a_enabled:
        return 0x01
    if b_enabled:
        return 0x02
    return 0x00


def _normalize_service_uuids(service_uuids: Iterable[str] | None) -> set[str]:
    if service_uuids is None:
        return set()
    return {str(item).lower() for item in service_uuids if item}


def _high(value: int) -> int:
    clipped = max(0, min(int(value), 0xFFFF))
    return (clipped >> 8) & 0xFF


def _low(value: int) -> int:
    clipped = max(0, min(int(value), 0xFFFF))
    return clipped & 0xFF


def _compute_checksum(values: Iterable[int]) -> int:
    total = 0
    for item in values:
        total = (total + item) & 0xFF
    return total


def _build_ems_query_packet(query_type: int) -> bytes:
    values = [0x35, 0x71, max(0, min(int(query_type), 0xFF))]
    values.append(_compute_checksum(values))
    return bytes(values)


def _try_parse_ems_battery_level(packet: bytes) -> int | None:
    if len(packet) < 4 or packet[0] != 0x35 or packet[1] != 0x71 or packet[2] != 0x04:
        return None
    return max(0, min(int(packet[3]), 100))


# ── Toy 协议包构建与解析 ─────────────────────────────────────────────────

def create_toy_speed_packet(step: ToyWaveformStep) -> bytes:
    """构建 Toy 实时速率控制包: 35 12 motor_a motor_b motor_c checksum"""
    values = [0x35, 0x12, _clamp_toy_speed(step.motor_a), _clamp_toy_speed(step.motor_b), _clamp_toy_speed(step.motor_c)]
    values.append(_compute_checksum(values))
    return bytes(values)


def create_toy_stop_packet() -> bytes:
    """构建 Toy 停止包: 所有马达速率归零。"""
    return create_toy_speed_packet(ToyWaveformStep())


def _build_toy_device_info_query() -> bytes:
    """构建 Toy 设备信息查询包: 35 10 checksum"""
    values = [0x35, 0x10]
    values.append(_compute_checksum(values))
    return bytes(values)


def _clamp_toy_speed(value: int) -> int:
    return max(0, min(int(value), 20))


def _ems_step_to_toy(step: EmsWaveformStep) -> ToyWaveformStep:
    """将 EMS 波形步骤转换为 Toy 马达步骤：强度 0-180 映射到速度 0-20。"""
    motor_a = int(step.channel_a / 180 * 20)
    motor_b = int(step.channel_b / 180 * 20)
    return ToyWaveformStep(
        duration_ms=max(1, step.duration_ms),
        motor_a=motor_a,
        motor_b=motor_b,
        motor_c=0,
    )


def _try_parse_toy_notify(data: bytes) -> dict | None:
    """解析 Toy 设备通知包。"""
    if len(data) < 3 or data[0] != 0x35:
        return None
    cmd = data[1]
    if cmd == 0x13 and len(data) >= 5 and data[2] == 0x01:
        return {"type": "battery", "level": max(0, min(int(data[3]), 100))}
    if cmd == 0x10 and len(data) >= 10:
        return {
            "type": "device_info",
            "motor_a_modes": data[4],
            "motor_b_modes": data[5],
            "motor_c_modes": data[6],
        }
    if cmd == 0x14:
        return {"type": "heartbeat"}
    return None
