from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from app.runtime import resolve_bundle_path
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(resolve_bundle_path("app/templates")))

router = APIRouter()


class StartSessionRequest(BaseModel):
    mode: str
    value: str
    trigger_mode: str = "by_quantity"
    like_multiple: int = 100
    danmaku_enabled: bool = False
    danmaku_keywords: str = ""
    danmaku_cooldown_seconds: int = 0


class ConnectCommandRequest(BaseModel):
    ws_url: str
    uid: str
    token: str


class ConnectBluetoothRequest(BaseModel):
    device_id: str


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
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


@router.post("/api/bluetooth/scan")
async def scan_bluetooth_devices(request: Request) -> dict:
    devices = await request.app.state.bluetooth_service.scan()
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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


@router.post("/api/session/start")
async def start_session(request: Request, payload: StartSessionRequest) -> dict:
    try:
        await request.app.state.session_service.start(
            mode=payload.mode,
            value=payload.value,
            trigger_mode=payload.trigger_mode,
            like_multiple=payload.like_multiple,
            danmaku_enabled=payload.danmaku_enabled,
            danmaku_keywords=payload.danmaku_keywords,
            danmaku_cooldown_seconds=payload.danmaku_cooldown_seconds,
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


def _read_bluetooth_value(item: object, key: str):
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key)
