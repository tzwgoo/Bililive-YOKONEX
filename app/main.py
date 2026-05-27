from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.bluetooth.dispatcher import BluetoothDispatcher
from app.bluetooth.service import BluetoothService
from app.bilibili.http_client import BilibiliOpenClient
from app.bilibili.ws_client import BilibiliWsClient
from app.command_gateway.mapping import GiftCommandMapper
from app.config import Settings, load_settings
from app.logging_config import setup_logging
from app.runtime import resolve_bundle_path, resolve_runtime_path
from app.services.command_session import CommandSessionService
from app.services.danmaku_dispatcher import DanmakuCommandDispatcher
from app.services.event_hub import EventHub
from app.services.gift_dispatcher import GiftCommandDispatcher
from app.services.live_session_manager import LiveSessionManager
from app.services.open_live_session import OpenLiveSessionService


BASE_DIR = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="Bilibili Live Interaction")

    config_error = ""
    settings: Settings | None = None
    try:
        settings = load_settings()
    except ValueError as exc:
        config_error = str(exc)

    event_hub = EventHub()
    api_client = None
    if settings is not None:
        api_client = BilibiliOpenClient(
            base_url="https://live-open.biliapi.com",
            access_key_id=settings.access_key_id,
            access_key_secret=settings.access_key_secret,
        )
    mapping_path = Path(settings.gift_mapping_path) if settings is not None else Path("config/gift_command_mappings.json")
    if not mapping_path.is_absolute():
        mapping_path = resolve_runtime_path(str(mapping_path))
    mapper = GiftCommandMapper.from_file(mapping_path)
    command_session = CommandSessionService()
    bluetooth_service = BluetoothService.create_default(
        config_path=resolve_runtime_path("config/bluetooth_settings.json"),
    )
    gift_dispatcher = GiftCommandDispatcher(
        mapper=mapper,
        command_session=command_session,
    )
    danmaku_dispatcher = DanmakuCommandDispatcher(
        command_session=command_session,
    )
    bluetooth_dispatcher = BluetoothDispatcher(
        bluetooth_service=bluetooth_service,
    )
    ws_client = BilibiliWsClient()
    open_live_session = OpenLiveSessionService(
        settings=settings,
        event_hub=event_hub,
        api_client=api_client,
        ws_client=ws_client,
        gift_dispatcher=gift_dispatcher,
        danmaku_dispatcher=danmaku_dispatcher,
        bluetooth_dispatcher=bluetooth_dispatcher,
        config_error=config_error,
    )
    from app.services.third_party_session import ThirdPartyLiveSessionService

    third_party_session = ThirdPartyLiveSessionService(
        event_hub=event_hub,
        gift_dispatcher=gift_dispatcher,
        danmaku_dispatcher=danmaku_dispatcher,
        bluetooth_dispatcher=bluetooth_dispatcher,
    )
    session_service = LiveSessionManager(
        open_live_session=open_live_session,
        third_party_session=third_party_session,
    )

    app.state.event_hub = event_hub
    app.state.bluetooth_service = bluetooth_service
    app.state.command_session = command_session
    app.state.session_service = session_service
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=str(resolve_bundle_path("app/static"))), name="static")
    return app


app = create_app()
