from __future__ import annotations

import asyncio

import pytest

from management_server.hub import DeviceConnectionHub


class FakeWebSocket:
    def __init__(self, hub: DeviceConnectionHub) -> None:
        self.hub = hub
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)
        asyncio.get_running_loop().call_soon(
            self.hub.resolve_result,
            {
                "type": "device.command_result",
                "request_id": payload["request_id"],
                "success": True,
                "message": "执行成功",
            },
        )

    async def close(self, **_kwargs) -> None:
        return None


@pytest.mark.anyio
async def test_device_hub_sends_command_and_waits_for_result() -> None:
    hub = DeviceConnectionHub()
    websocket = FakeWebSocket(hub)
    await hub.register("client-1", websocket)  # type: ignore[arg-type]

    result = await hub.send_command(
        client_id="client-1",
        payload={"type": "device.command", "request_id": "request-1"},
        timeout_seconds=1,
    )

    assert websocket.sent[0]["request_id"] == "request-1"
    assert result["success"] is True
