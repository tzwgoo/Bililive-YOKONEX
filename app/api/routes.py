from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from app.runtime import resolve_bundle_path
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(resolve_bundle_path("app/templates")))

router = APIRouter()


def _spa_index_path() -> Path:
    return resolve_bundle_path("frontend/dist/index.html")


def _spa_index_response() -> FileResponse | None:
    spa_index = _spa_index_path()
    if spa_index.exists():
        return FileResponse(spa_index)
    return None


class StartSessionRequest(BaseModel):
    mode: str = "third_party"
    value: str
    connection_mode: str | None = None
    output_mode: str | None = None
    trigger_mode: str = "by_quantity"
    like_multiple: int = 100
    danmaku_enabled: bool = False
    danmaku_keywords: str = ""
    danmaku_cooldown_seconds: int = 0
    danmaku_user_limit_window_seconds: int = 0
    danmaku_user_limit_max_triggers: int = 0
    danmaku_min_guard_level: int = 0


class ConnectCommandRequest(BaseModel):
    ws_url: str
    uid: str
    token: str


class ConnectBluetoothRequest(BaseModel):
    device_id: str


class BluetoothRuleUpdateItem(BaseModel):
    id: str
    enabled: bool
    waveform_id: str
    min_price: int | None = None
    max_price: int | None = None
    guard_waveforms: dict[str, dict[str, str]] | None = None


class UpdateBluetoothRulesRequest(BaseModel):
    rules: list[BluetoothRuleUpdateItem]


class CreateBluetoothWaveformRequest(BaseModel):
    name: str = ""
    device_type: str = "ems"


class DuplicateBluetoothWaveformRequest(BaseModel):
    name: str = ""


class BluetoothWaveformStepPayload(BaseModel):
    duration_ms: int
    channel_a: int = 0
    channel_b: int = 0
    motor_a: int = 0
    motor_b: int = 0
    motor_c: int = 0


class UpdateBluetoothWaveformRequest(BaseModel):
    name: str
    steps: list[BluetoothWaveformStepPayload]


class CommandGiftRuleUpdateItem(BaseModel):
    id: str
    enabled: bool = True
    event_type: str = "gift"
    min_price: int = 0
    max_price: int | None = None
    command_slot: str = ""


class CommandLikeRuleUpdateItem(BaseModel):
    id: str
    enabled: bool = True
    like_multiple: int = 100
    command_slot: str = ""


class CommandDanmakuSlotRuleUpdateItem(BaseModel):
    id: str
    enabled: bool = False
    event_type: str = "danmaku"
    guard_level: int = 0
    command_slot: str = ""


class UpdateCommandStudioRequest(BaseModel):
    rules: list[CommandGiftRuleUpdateItem]
    like_rules: list[CommandLikeRuleUpdateItem] = Field(default_factory=list)
    danmaku_slot_rules: list[CommandDanmakuSlotRuleUpdateItem] = Field(default_factory=list)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    spa_response = _spa_index_response()
    if spa_response is not None:
        return spa_response
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@router.get("/bluetooth/studio", response_class=HTMLResponse)
async def bluetooth_studio(request: Request) -> HTMLResponse:
    spa_response = _spa_index_response()
    if spa_response is not None:
        return spa_response
    return templates.TemplateResponse(
        request=request,
        name="bluetooth_studio.html",
        context={},
    )


@router.get("/command/studio", response_class=HTMLResponse)
async def command_studio(request: Request) -> HTMLResponse:
    spa_response = _spa_index_response()
    if spa_response is not None:
        return spa_response
    return templates.TemplateResponse(
        request=request,
        name="command_studio.html",
        context={},
    )


@router.get("/events", response_class=HTMLResponse)
async def events_page(request: Request) -> HTMLResponse:
    spa_response = _spa_index_response()
    if spa_response is not None:
        return spa_response
    return templates.TemplateResponse(
        request=request,
        name="command_studio.html",
        context={},
    )


@router.get("/waveforms", response_class=HTMLResponse)
async def waveforms_page(request: Request) -> HTMLResponse:
    spa_response = _spa_index_response()
    if spa_response is not None:
        return spa_response
    return templates.TemplateResponse(
        request=request,
        name="bluetooth_studio.html",
        context={},
    )


@router.get("/bluetooth/overlay", response_class=HTMLResponse)
async def bluetooth_overlay(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="bluetooth_overlay.html",
        context={"overlay_style": "panel"},
    )


@router.get("/api/status")
async def get_status(request: Request) -> dict:
    return request.app.state.session_service.get_status_payload()


@router.get("/api/command/status")
async def get_command_status(request: Request) -> dict:
    return request.app.state.command_session.get_status_payload()


@router.get("/api/bluetooth/status")
async def get_bluetooth_status(request: Request) -> dict:
    return request.app.state.bluetooth_service.get_status_payload()


@router.get("/api/bluetooth/studio")
async def get_bluetooth_studio_data(request: Request) -> dict:
    return request.app.state.bluetooth_service.get_studio_payload()


@router.get("/api/command/studio")
async def get_command_studio_data(request: Request) -> dict:
    return request.app.state.command_rule_service.get_studio_payload()


@router.get("/api/bluetooth/overlay/status")
async def get_bluetooth_overlay_status(request: Request, device_id: str | None = None) -> dict:
    if device_id:
        return request.app.state.bluetooth_service.get_overlay_payload(device_id)
    return request.app.state.bluetooth_service.get_overlay_payload()


@router.post("/api/bluetooth/scan")
async def scan_bluetooth_devices(request: Request) -> dict:
    try:
        devices = await request.app.state.bluetooth_service.scan()
    except (ValueError, RuntimeError, TimeoutError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "success": True,
        "devices": [
            {
                "device_id": _read_bluetooth_value(item, "device_id"),
                "name": _read_bluetooth_value(item, "name"),
                "device_type": _read_bluetooth_value(item, "device_type"),
                "protocol": _read_bluetooth_value(item, "protocol"),
                "rssi": _read_bluetooth_value(item, "rssi"),
                "connected": _read_bluetooth_value(item, "connected"),
            }
            for item in devices
        ],
    }


@router.post("/api/bluetooth/connect")
async def connect_bluetooth_device(request: Request, payload: ConnectBluetoothRequest) -> dict:
    try:
        status = await request.app.state.bluetooth_service.connect(payload.device_id)
    except (ValueError, RuntimeError, TimeoutError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    handle_bluetooth_connected = getattr(
        request.app.state.session_service,
        "handle_bluetooth_connected",
        None,
    )
    if callable(handle_bluetooth_connected):
        handle_bluetooth_connected()
    return {
        "success": True,
        "connected": status.connected,
        "message": status.message,
    }


@router.post("/api/bluetooth/disconnect")
async def disconnect_bluetooth_device(request: Request) -> dict:
    status = await request.app.state.bluetooth_service.disconnect()
    return {
        "success": True,
        "connected": status.connected,
        "message": status.message,
    }


@router.post("/api/bluetooth/rules")
async def update_bluetooth_rules(request: Request, payload: UpdateBluetoothRulesRequest) -> dict:
    try:
        return request.app.state.bluetooth_service.save_rules(
            [item.model_dump() for item in payload.rules]
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/command/studio")
async def update_command_studio(
    request: Request,
    payload: UpdateCommandStudioRequest,
) -> dict:
    try:
        return request.app.state.command_rule_service.save_rules(
            {
                "rules": [item.model_dump() for item in payload.rules],
                "like_rules": [item.model_dump() for item in payload.like_rules],
                "danmaku_slot_rules": [item.model_dump() for item in payload.danmaku_slot_rules],
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/bluetooth/waveforms")
async def create_bluetooth_waveform(request: Request, payload: CreateBluetoothWaveformRequest) -> dict:
    try:
        return request.app.state.bluetooth_service.create_waveform(name=payload.name, device_type=payload.device_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/bluetooth/waveforms/{waveform_id}/duplicate")
async def duplicate_bluetooth_waveform(
    request: Request,
    waveform_id: str,
    payload: DuplicateBluetoothWaveformRequest,
) -> dict:
    try:
        return request.app.state.bluetooth_service.duplicate_waveform(
            source_waveform_id=waveform_id,
            name=payload.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/bluetooth/waveforms/{waveform_id}/play")
async def preview_bluetooth_waveform(
    request: Request,
    waveform_id: str,
    device_id: str | None = None,
) -> dict:
    try:
        if device_id:
            return await request.app.state.bluetooth_service.preview_waveform(waveform_id, device_id=device_id)
        return await request.app.state.bluetooth_service.preview_waveform(waveform_id)
    except (ValueError, RuntimeError, TimeoutError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/api/bluetooth/waveforms/{waveform_id}")
async def update_bluetooth_waveform(
    request: Request,
    waveform_id: str,
    payload: UpdateBluetoothWaveformRequest,
) -> dict:
    if not payload.steps:
        raise HTTPException(status_code=400, detail="波形至少需要一个分段")
    try:
        return request.app.state.bluetooth_service.update_waveform(
            waveform_id=waveform_id,
            name=payload.name,
            steps=[item.model_dump() for item in payload.steps],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/bluetooth/waveforms/{waveform_id}")
async def delete_bluetooth_waveform(request: Request, waveform_id: str) -> dict:
    try:
        return request.app.state.bluetooth_service.delete_waveform(waveform_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/bluetooth/overlay/stream")
async def bluetooth_overlay_stream(
    request: Request,
    once: bool = False,
    device_id: str | None = None,
) -> StreamingResponse:
    bluetooth_service = request.app.state.bluetooth_service

    async def generate():
        last_revision: int | None = None
        while True:
            if await request.is_disconnected():
                break
            payload = bluetooth_service.get_overlay_payload(device_id) if device_id else bluetooth_service.get_overlay_payload()
            current_revision = max(0, int(payload.get("revision", 0) or 0))
            # 只在状态实际变化时推送，避免多设备叠加窗被高频全量重绘拖慢。
            if last_revision != current_revision or once:
                last_revision = current_revision
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            if once:
                break
            await asyncio.sleep(0.12)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/api/session/start")
async def start_session(request: Request, payload: StartSessionRequest) -> dict:
    try:
        normalized_connection_mode = payload.connection_mode or payload.output_mode or ""
        await request.app.state.session_service.start(
            mode=payload.mode,
            value=payload.value,
            output_mode=normalized_connection_mode,
            trigger_mode=payload.trigger_mode,
            like_multiple=payload.like_multiple,
            danmaku_enabled=payload.danmaku_enabled,
            danmaku_keywords=payload.danmaku_keywords,
            danmaku_cooldown_seconds=payload.danmaku_cooldown_seconds,
            danmaku_user_limit_window_seconds=payload.danmaku_user_limit_window_seconds,
            danmaku_user_limit_max_triggers=payload.danmaku_user_limit_max_triggers,
            danmaku_min_guard_level=payload.danmaku_min_guard_level,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True}


@router.post("/api/session/stop")
async def stop_session(request: Request) -> dict:
    await request.app.state.session_service.stop()
    return {"success": True}


@router.post("/api/command/connect")
async def connect_command(request: Request, payload: ConnectCommandRequest) -> dict:
    try:
        status = await request.app.state.command_session.connect(
            ws_url=payload.ws_url,
            uid=payload.uid,
            token=payload.token,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "status": status}


@router.post("/api/command/disconnect")
async def disconnect_command(request: Request) -> dict:
    await request.app.state.command_session.disconnect()
    return {"success": True}


@router.get("/api/events/stream")
async def event_stream(request: Request) -> StreamingResponse:
    event_hub = request.app.state.event_hub

    async def generate():
        queue = event_hub.subscribe()
        try:
            for item in event_hub.snapshot():
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            event_hub.unsubscribe(queue)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/api/control/stream")
async def control_stream(request: Request, once: bool = False) -> StreamingResponse:
    event_hub = request.app.state.event_hub

    async def generate():
        queue = event_hub.subscribe_control()
        try:
            for item in event_hub.control_snapshot():
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
                if once:
                    return
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if once:
                    return
        finally:
            event_hub.unsubscribe_control(queue)

    return StreamingResponse(generate(), media_type="text/event-stream")


def _read_bluetooth_value(item: object, key: str):
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key)
