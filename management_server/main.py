from __future__ import annotations

import asyncio
import secrets
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.remote_control.protocol import ALLOWED_ACTIONS, COMMAND_IDS
from management_server.config import ManagementSettings, load_management_settings
from management_server.hub import DeviceConnectionHub
from management_server.security import AdminSession, AdminSessionManager, LoginRateLimiter
from management_server.store import ManagementStore


BASE_DIR = Path(__file__).resolve().parent
SESSION_COOKIE = "bililive_management_session"


class LoginRequest(BaseModel):
    username: str
    password: str


class CommandRequest(BaseModel):
    action: str
    args: dict[str, Any] = Field(default_factory=dict)


def create_management_app(settings: ManagementSettings | None = None) -> FastAPI:
    settings = settings or load_management_settings()
    settings.validate()
    store = ManagementStore(settings.database_path)
    store.initialize()
    hub = DeviceConnectionHub()
    sessions = AdminSessionManager(session_seconds=settings.session_hours * 3600)
    login_limiter = LoginRateLimiter()
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

    app = FastAPI(title="BiliLive 设备管理中心")
    app.state.settings = settings
    app.state.store = store
    app.state.hub = hub
    app.state.sessions = sessions
    app.mount("/admin/static", StaticFiles(directory=str(BASE_DIR / "static")), name="management-static")

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse("/admin")

    @app.get("/admin/login", response_class=HTMLResponse, include_in_schema=False)
    async def login_page(request: Request) -> Any:
        if _get_session(request, sessions) is not None:
            return RedirectResponse("/admin", status_code=303)
        return templates.TemplateResponse(request=request, name="login.html", context={})

    @app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard_page(request: Request) -> Any:
        if _get_session(request, sessions) is None:
            return RedirectResponse("/admin/login", status_code=303)
        return templates.TemplateResponse(request=request, name="dashboard.html", context={})

    @app.post("/api/admin/login")
    async def login(request: Request, payload: LoginRequest) -> JSONResponse:
        client_key = request.client.host if request.client else "unknown"
        if not login_limiter.allow(client_key):
            raise HTTPException(status_code=429, detail="登录失败次数过多，请稍后重试")
        username_ok = secrets.compare_digest(payload.username, settings.admin_username)
        password_ok = secrets.compare_digest(payload.password, settings.admin_password)
        if not username_ok or not password_ok:
            login_limiter.record_failure(client_key)
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        login_limiter.clear(client_key)
        session = sessions.create()
        response = JSONResponse({"success": True, "csrf_token": session.csrf_token})
        response.set_cookie(
            SESSION_COOKIE,
            session.token,
            httponly=True,
            samesite="strict",
            secure=settings.cookie_secure,
            max_age=settings.session_hours * 3600,
        )
        return response

    @app.get("/api/admin/me")
    async def current_admin(request: Request) -> dict[str, Any]:
        session = _require_session(request, sessions)
        return {
            "username": settings.admin_username,
            "csrf_token": session.csrf_token,
            "expires_at": session.expires_at,
        }

    @app.post("/api/admin/logout")
    async def logout(request: Request) -> JSONResponse:
        session = _require_session(request, sessions)
        _require_csrf(request, session)
        sessions.revoke(session.token)
        response = JSONResponse({"success": True})
        response.delete_cookie(SESSION_COOKIE)
        return response

    @app.get("/api/admin/clients")
    async def list_clients(request: Request) -> dict[str, Any]:
        _require_session(request, sessions)
        clients = store.list_clients(hub.online_client_ids)
        return {
            "clients": clients,
            "online_count": sum(1 for item in clients if item["online"]),
            "total_count": len(clients),
        }

    @app.get("/api/admin/clients/{client_id}")
    async def get_client(request: Request, client_id: str) -> dict[str, Any]:
        _require_session(request, sessions)
        client = store.get_client(client_id, online=client_id in hub.online_client_ids)
        if client is None:
            raise HTTPException(status_code=404, detail="客户端不存在")
        return client

    @app.post("/api/admin/clients/{client_id}/commands")
    async def send_command(request: Request, client_id: str, payload: CommandRequest) -> dict[str, Any]:
        session = _require_session(request, sessions)
        _require_csrf(request, session)
        if payload.action not in ALLOWED_ACTIONS:
            raise HTTPException(status_code=400, detail="不支持的远程操作")
        if client_id not in hub.online_client_ids:
            raise HTTPException(status_code=409, detail="客户端当前不在线")

        args = _validate_command_args(store, client_id, payload.action, payload.args)
        request_id = uuid.uuid4().hex
        command_payload = {
            "type": "device.command",
            "request_id": request_id,
            "action": payload.action,
            "args": args,
            "issued_at": int(time.time()),
            "expires_at": int(time.time()) + 30,
        }
        store.create_command(request_id, client_id, payload.action, args)
        # 固定输出需要等设备完成并发送停止包，超时必须覆盖最长 60 秒执行时间。
        command_timeout = (
            int(args.get("duration_seconds", 0)) + 10
            if payload.action == "output.fixed"
            else 30
        )
        try:
            result = await hub.send_command(
                client_id=client_id,
                payload=command_payload,
                timeout_seconds=command_timeout,
            )
        except (RuntimeError, asyncio.TimeoutError) as exc:
            message = "客户端执行超时" if isinstance(exc, asyncio.TimeoutError) else str(exc)
            store.fail_command(request_id, message)
            raise HTTPException(status_code=504, detail=message) from exc
        success = bool(result.get("success"))
        message = str(result.get("message", "") or "")
        store.finish_command(request_id, success=success, message=message)
        return {"request_id": request_id, **result}

    @app.websocket("/device/ws")
    async def device_websocket(websocket: WebSocket) -> None:
        await websocket.accept()
        client_id = ""
        try:
            first_message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
            message_type = str(first_message.get("type", ""))
            if message_type == "device.enroll":
                supplied_token = str(first_message.get("registration_token", "") or "")
                if not secrets.compare_digest(supplied_token, settings.registration_token):
                    await websocket.send_json({"type": "error", "message": "设备注册密钥无效"})
                    await websocket.close(code=1008)
                    return
                client_id, device_token = store.enroll_client(
                    client_name=str(first_message.get("client_name", "") or ""),
                    platform=str(first_message.get("platform", "") or ""),
                )
                await websocket.send_json({
                    "type": "device.enrolled",
                    "client_id": client_id,
                    "device_token": device_token,
                })
            elif message_type == "device.authenticate":
                client_id = str(first_message.get("client_id", "") or "")
                device_token = str(first_message.get("device_token", "") or "")
                if not store.authenticate_client(client_id, device_token):
                    await websocket.send_json({"type": "error", "message": "设备认证失败"})
                    await websocket.close(code=1008)
                    return
                await websocket.send_json({"type": "device.authenticated", "client_id": client_id})
            else:
                await websocket.send_json({"type": "error", "message": "请先完成设备认证"})
                await websocket.close(code=1008)
                return

            await hub.register(client_id, websocket)
            while True:
                message = await websocket.receive_json()
                message_type = str(message.get("type", ""))
                if message_type == "device.heartbeat":
                    store.update_heartbeat(client_id, message)
                elif message_type == "device.capabilities":
                    store.sync_capabilities(client_id, message)
                elif message_type == "device.command_result":
                    hub.resolve_result(message)
                elif message_type == "pong":
                    continue
        except (WebSocketDisconnect, asyncio.TimeoutError):
            pass
        finally:
            if client_id:
                hub.unregister(client_id, websocket)

    return app


def _get_session(request: Request, sessions: AdminSessionManager) -> AdminSession | None:
    return sessions.get(str(request.cookies.get(SESSION_COOKIE, "") or ""))


def _require_session(request: Request, sessions: AdminSessionManager) -> AdminSession:
    session = _get_session(request, sessions)
    if session is None:
        raise HTTPException(status_code=401, detail="请先登录")
    return session


def _require_csrf(request: Request, session: AdminSession) -> None:
    supplied_token = str(request.headers.get("X-CSRF-Token", "") or "")
    if not secrets.compare_digest(supplied_token, session.csrf_token):
        raise HTTPException(status_code=403, detail="请求校验失败，请刷新页面后重试")


def _validate_command_args(
    store: ManagementStore,
    client_id: str,
    action: str,
    incoming: dict[str, Any],
) -> dict[str, Any]:
    if action == "command.send":
        command_id = str(incoming.get("command_id", "") or "")
        if command_id not in COMMAND_IDS:
            raise HTTPException(status_code=400, detail="不支持的 commandId")
        client = store.get_client(client_id, online=True)
        if client is None or command_id not in client["command_ids"]:
            raise HTTPException(status_code=400, detail="客户端未声明支持该 commandId")
        return {"command_id": command_id}

    device_id = str(incoming.get("device_id", "") or "")
    device = store.get_device(client_id, device_id)
    if not device_id or device is None:
        raise HTTPException(status_code=400, detail="设备不存在")
    if action != "device.disconnect" and not device["connected"]:
        raise HTTPException(status_code=409, detail="设备当前未连接")
    if action in {"waveform.stop", "device.disconnect"}:
        return {"device_id": device_id}
    if action == "output.fixed":
        try:
            strength = int(incoming.get("strength", 0))
            duration_seconds = int(incoming.get("duration_seconds", 0))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="强度和时长必须是整数") from exc
        if not 1 <= duration_seconds <= 60:
            raise HTTPException(status_code=400, detail="固定输出时长只能是 1 到 60 秒")
        protocol = str(device.get("protocol", ""))
        if "gcq" in protocol:
            raise HTTPException(status_code=400, detail="灌肠机不支持单一固定强度控制")
        max_strength = 20 if str(device.get("device_type", "")) == "toy" else 180
        if not 1 <= strength <= max_strength:
            raise HTTPException(status_code=400, detail=f"当前设备强度只能是 1 到 {max_strength}")
        return {
            "device_id": device_id,
            "strength": strength,
            "duration_seconds": duration_seconds,
        }

    waveform_id = str(incoming.get("waveform_id", "") or "")
    waveform = store.get_waveform(client_id, waveform_id)
    if waveform is None:
        raise HTTPException(status_code=400, detail="波形不存在或已经失效")
    _validate_waveform_device(waveform, device)
    return {
        "device_id": device_id,
        "waveform_id": waveform_id,
        # 哈希由服务端数据库读取，不信任浏览器提交的版本值。
        "version_hash": waveform["version_hash"],
    }


def _validate_waveform_device(waveform: dict[str, Any], device: dict[str, Any]) -> None:
    waveform_type = str(waveform.get("waveform_type", ""))
    device_type = str(device.get("device_type", ""))
    if waveform_type == "toy" and device_type != "toy":
        raise HTTPException(status_code=400, detail="Toy 波形与目标设备不兼容")
    if waveform_type == "ems" and device_type == "toy":
        raise HTTPException(status_code=400, detail="EMS 波形与目标设备不兼容")
    family = str(waveform.get("device_family", ""))
    protocol = str(device.get("protocol", ""))
    if family == "gcq" and "gcq" not in protocol:
        raise HTTPException(status_code=400, detail="灌肠机波形与目标设备不兼容")
    if family == "toy" and "gcq" in protocol:
        raise HTTPException(status_code=400, detail="普通 Toy 波形与灌肠机设备不兼容")
