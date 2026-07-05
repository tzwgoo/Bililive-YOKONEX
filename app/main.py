from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.bluetooth.dispatcher import BluetoothDispatcher
from app.bluetooth.service import BluetoothService
from app.command_gateway.mapping import GiftCommandMapper
from app.config import Settings, load_settings
from app.logging_config import setup_logging
from app.runtime import ensure_persistent_file, resolve_bundle_path, resolve_persistent_path
from app.services.command_session import CommandSessionService
from app.services.command_rule_service import CommandRuleService
from app.services.danmaku_dispatcher import DanmakuCommandDispatcher
from app.services.douyin_session import DouyinLiveSessionService
from app.services.event_hub import EventHub
from app.services.gift_dispatcher import GiftCommandDispatcher
from app.services.live_session_manager import LiveSessionManager
from app.services.third_party_session import ThirdPartyLiveSessionService


BASE_DIR = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="Bilibili Live Interaction")

    settings: Settings = load_settings()

    event_hub = EventHub()
    mapping_path = Path(settings.gift_mapping_path)
    if not mapping_path.is_absolute():
        mapping_path = ensure_persistent_file(
            str(mapping_path),
            default_source_path=resolve_bundle_path("config/gift_command_mappings.json"),
        )
    mapper = GiftCommandMapper.from_file(mapping_path)
    command_session = CommandSessionService(event_hub=event_hub)
    bluetooth_service = BluetoothService.create_default(
        config_path=resolve_persistent_path("config/bluetooth_settings.json"),
        event_hub=event_hub,
    )
    gift_dispatcher = GiftCommandDispatcher(
        mapper=mapper,
        command_session=command_session,
    )
    danmaku_dispatcher = DanmakuCommandDispatcher(
        command_session=command_session,
    )
    command_rule_service = CommandRuleService(
        config_path=mapping_path,
        mapper=mapper,
        danmaku_dispatcher=danmaku_dispatcher,
    )
    bluetooth_dispatcher = BluetoothDispatcher(
        bluetooth_service=bluetooth_service,
    )
    third_party_session = ThirdPartyLiveSessionService(
        event_hub=event_hub,
        gift_dispatcher=gift_dispatcher,
        danmaku_dispatcher=danmaku_dispatcher,
        bluetooth_dispatcher=bluetooth_dispatcher,
    )
    douyin_session = DouyinLiveSessionService(
        event_hub=event_hub,
        gift_dispatcher=gift_dispatcher,
        danmaku_dispatcher=danmaku_dispatcher,
        bluetooth_dispatcher=bluetooth_dispatcher,
    )
    session_service = LiveSessionManager(
        third_party_session=third_party_session,
        douyin_session=douyin_session,
        command_session=command_session,
        bluetooth_service=bluetooth_service,
    )

    app.state.event_hub = event_hub
    app.state.bluetooth_service = bluetooth_service
    app.state.command_session = command_session
    app.state.command_rule_service = command_rule_service
    app.state.session_service = session_service
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=str(resolve_bundle_path("app/static"))), name="static")
    frontend_assets_dir = resolve_bundle_path("frontend/dist/assets")
    if frontend_assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_assets_dir)), name="frontend-assets")
    return app


app = create_app()
