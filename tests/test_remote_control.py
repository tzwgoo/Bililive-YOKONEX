from __future__ import annotations

import pytest

from app.bluetooth.models import BluetoothConfigPayload, EmsWaveform, EmsWaveformStep
from app.bluetooth.runtime.memory_runtime import MemoryBluetoothRuntime
from app.bluetooth.service import BluetoothService
from app.bluetooth.storage import BluetoothSettingsStore
from app.remote_control.command_handler import RemoteCommandHandler
from app.remote_control.identity import DeviceIdentity, DeviceIdentityStore


class FakeCommandSession:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_command(self, *, command_id: str) -> dict:
        self.sent.append(command_id)
        return {"success": True, "message": "发送成功"}


class FakeBluetoothService:
    def __init__(self) -> None:
        self.fixed_outputs: list[dict] = []

    def get_remote_waveform_summary(self, waveform_id: str) -> dict:
        return {
            "waveform_id": waveform_id,
            "waveform_type": "ems",
            "device_family": "ems",
            "version_hash": "hash-1",
        }

    def get_status_payload(self) -> dict:
        return {
            "devices": [{
                "device_id": "ems-1",
                "device_type": "ems",
                "protocol": "ems_v1",
                "connected": True,
            }]
        }

    async def trigger_waveform(self, **kwargs) -> dict:
        return {"success": True, "message": "波形已播放", **kwargs}

    async def trigger_fixed_output(self, **kwargs) -> dict:
        self.fixed_outputs.append(kwargs)
        return {"success": True, "message": "固定输出完成", **kwargs}


def test_identity_store_round_trip(tmp_path) -> None:
    store = DeviceIdentityStore(tmp_path / "identity.json")

    store.save(DeviceIdentity(client_id="client-1", device_token="secret"))

    assert store.load() == DeviceIdentity(client_id="client-1", device_token="secret")


def test_remote_capabilities_only_include_waveform_summary(tmp_path) -> None:
    payload = BluetoothConfigPayload(
        ems_waveforms=[EmsWaveform(
            id="wave-1",
            name="测试波形",
            steps=[EmsWaveformStep(duration_ms=200, channel_a=30)],
        )]
    )
    service = BluetoothService(
        store=BluetoothSettingsStore(tmp_path / "bluetooth.json"),
        runtime=MemoryBluetoothRuntime(),
        payload=payload,
    )

    capabilities = service.get_remote_capabilities_payload()

    assert capabilities["waveforms"][0]["waveform_id"] == "wave-1"
    assert "steps" not in capabilities["waveforms"][0]
    assert len(capabilities["waveforms"][0]["version_hash"]) == 64
    previous_revision = capabilities["waveform_revision"]
    payload.ems_waveforms[0].steps[0].channel_a = 31
    assert service.get_remote_capabilities_payload()["waveform_revision"] != previous_revision


@pytest.mark.anyio
async def test_remote_handler_rejects_unknown_command_id() -> None:
    handler = RemoteCommandHandler(
        command_session=FakeCommandSession(),
        bluetooth_service=FakeBluetoothService(),
    )

    with pytest.raises(ValueError, match="不支持的 commandId"):
        await handler.execute("command.send", {"command_id": "system.shell"})


@pytest.mark.anyio
async def test_remote_handler_checks_waveform_version() -> None:
    handler = RemoteCommandHandler(
        command_session=FakeCommandSession(),
        bluetooth_service=FakeBluetoothService(),
    )

    with pytest.raises(ValueError, match="波形已经发生变化"):
        await handler.execute("waveform.play", {
            "device_id": "ems-1",
            "waveform_id": "wave-1",
            "version_hash": "stale-hash",
        })


@pytest.mark.anyio
async def test_remote_handler_executes_supported_command() -> None:
    command_session = FakeCommandSession()
    handler = RemoteCommandHandler(
        command_session=command_session,
        bluetooth_service=FakeBluetoothService(),
    )

    result = await handler.execute("command.send", {"command_id": "command_one"})

    assert result["success"] is True
    assert command_session.sent == ["command_one"]


@pytest.mark.anyio
async def test_remote_handler_executes_fixed_output_with_device_limits() -> None:
    bluetooth_service = FakeBluetoothService()
    handler = RemoteCommandHandler(
        command_session=FakeCommandSession(),
        bluetooth_service=bluetooth_service,
    )

    result = await handler.execute("output.fixed", {
        "device_id": "ems-1",
        "strength": 80,
        "duration_seconds": 5,
    })

    assert result["success"] is True
    assert bluetooth_service.fixed_outputs == [{
        "device_id": "ems-1",
        "strength": 80,
        "duration_seconds": 5,
    }]

    with pytest.raises(ValueError, match="1 到 180"):
        await handler.execute("output.fixed", {
            "device_id": "ems-1",
            "strength": 181,
            "duration_seconds": 5,
        })


@pytest.mark.anyio
async def test_bluetooth_service_runs_fixed_output_without_saving_waveform(tmp_path) -> None:
    service = BluetoothService(
        store=BluetoothSettingsStore(tmp_path / "bluetooth.json"),
        runtime=MemoryBluetoothRuntime(),
    )
    scanned = await service.scan()
    await service.connect(scanned[0].device_id)
    before_ids = [item.id for item in service.payload.ems_waveforms]

    result = await service.trigger_fixed_output(
        device_id=scanned[0].device_id,
        strength=60,
        duration_seconds=3,
    )

    assert result["success"] is True
    assert result["strength"] == 60
    assert result["duration_seconds"] == 3
    assert [item.id for item in service.payload.ems_waveforms] == before_ids
