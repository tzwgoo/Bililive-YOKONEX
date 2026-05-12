# Bilibili 直播礼物互动程序 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个单直播间的 Python 本地 Web 面板服务，接入哔哩哔哩直播开放平台，实时展示礼物、弹幕、点赞事件，并支持双心跳、自动重连和优雅停止。

**Architecture:** FastAPI 提供本地页面与控制接口；`BilibiliOpenClient` 负责官方 HTTP 接口签名与调用；`BilibiliWsClient` 负责官方长连鉴权、协议解析和事件提取；`LiveSessionService` 负责单会话生命周期、项目心跳、长连心跳、重连与事件标准化；前端通过 SSE 获取实时事件并渲染本地面板。

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, httpx, websockets, asyncio, python-dotenv, pydantic, pytest

---

## File Map

- `requirements.txt`
  记录运行和测试依赖。
- `.env.example`
  提供 `APP_ID`、`BILI_ACCESS_KEY_ID`、`BILI_ACCESS_KEY_SECRET` 示例。
- `app/main.py`
  FastAPI 入口，注册路由、模板、静态资源、关闭钩子。
- `app/config.py`
  读取 `.env`、校验必填配置、对外暴露配置对象。
- `app/models.py`
  定义会话状态、标准化事件模型、前端响应模型。
- `app/bilibili/signature.py`
  负责 MD5、待签名字符串拼接、HMAC-SHA256 签名。
- `app/bilibili/http_client.py`
  封装 `/v2/app/start`、`/v2/app/heartbeat`、`/v2/app/end`。
- `app/bilibili/ws_protocol.py`
  负责协议头编码解码、zlib 解压、多包拆分。
- `app/bilibili/ws_client.py`
  负责官方 WebSocket 连接、鉴权、长连心跳、原始消息读取。
- `app/services/event_hub.py`
  维护最近事件缓存，提供 SSE 广播。
- `app/services/live_session.py`
  负责单会话启动、停止、双心跳、重连、事件标准化。
- `app/api/routes.py`
  暴露首页、启动、停止、状态、事件流接口。
- `app/templates/index.html`
  本地面板 HTML。
- `app/static/app.js`
  面板交互、状态轮询、SSE 事件消费。
- `app/static/style.css`
  面板样式。
- `logs/.gitkeep`
  预留日志目录。
- `tests/`
  单元测试与接口测试。
- `README.md`
  本地运行说明、联调步骤、常见错误说明。

## Task 1: 初始化项目骨架与配置加载

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config.py`
- Create: `app/models.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: 先写配置测试**

```python
from app.config import load_settings


def test_load_settings_requires_all_required_fields(monkeypatch):
    monkeypatch.delenv("APP_ID", raising=False)
    monkeypatch.delenv("BILI_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("BILI_ACCESS_KEY_SECRET", raising=False)

    try:
        load_settings()
    except ValueError as exc:
        assert "APP_ID" in str(exc)
    else:
        raise AssertionError("load_settings() should reject missing settings")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_config.py -v`

Expected: FAIL，报 `ModuleNotFoundError` 或 `ImportError`，说明配置模块尚未实现。

- [ ] **Step 3: 实现最小配置模块与基础依赖**

```python
# app/config.py
from dataclasses import dataclass
from dotenv import load_dotenv
import os


@dataclass(frozen=True)
class Settings:
    app_id: int
    access_key_id: str
    access_key_secret: str


def load_settings() -> Settings:
    load_dotenv()
    missing = [
        name for name in ("APP_ID", "BILI_ACCESS_KEY_ID", "BILI_ACCESS_KEY_SECRET")
        if not os.getenv(name)
    ]
    if missing:
        raise ValueError(f"Missing required settings: {', '.join(missing)}")
    return Settings(
        app_id=int(os.environ["APP_ID"]),
        access_key_id=os.environ["BILI_ACCESS_KEY_ID"],
        access_key_secret=os.environ["BILI_ACCESS_KEY_SECRET"],
    )
```

- [ ] **Step 4: 补齐基础文件**

```text
requirements.txt
fastapi
uvicorn
httpx
websockets
python-dotenv
pydantic
pytest
```

```env
# .env.example
APP_ID=1234567890123
BILI_ACCESS_KEY_ID=your_access_key_id
BILI_ACCESS_KEY_SECRET=your_access_key_secret
```

- [ ] **Step 5: 再次运行测试确认通过**

Run: `pytest tests/test_config.py -v`

Expected: PASS

- [ ] **Step 6: 提交当前阶段**

```bash
# 若当前目录已初始化 git
git add requirements.txt .env.example app/__init__.py app/main.py app/config.py app/models.py tests/test_config.py
git commit -m "feat(基础骨架): 初始化 Python 服务骨架与配置加载"
```

## Task 2: 实现官方签名与 HTTP API 客户端

**Files:**
- Create: `app/bilibili/__init__.py`
- Create: `app/bilibili/signature.py`
- Create: `app/bilibili/http_client.py`
- Create: `tests/test_signature.py`
- Create: `tests/test_http_client.py`

- [ ] **Step 1: 先写签名测试**

```python
from app.bilibili.signature import build_content_md5, build_signature


def test_build_content_md5_is_lowercase_hex():
    assert build_content_md5('{"app_id":1}') == "c9644e73c47aa4655bd18987e4ba65a4"
```

- [ ] **Step 2: 先写 HTTP 客户端测试**

```python
import httpx
import pytest

from app.bilibili.http_client import BilibiliOpenClient


@pytest.mark.asyncio
async def test_start_returns_json_payload():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/app/start"
        return httpx.Response(
            200,
            json={"code": 0, "message": "ok", "data": {"game_info": {"game_id": "g1"}}},
        )

    transport = httpx.MockTransport(handler)
    client = BilibiliOpenClient(
        base_url="https://live-open.biliapi.com",
        access_key_id="ak",
        access_key_secret="sk",
        transport=transport,
    )
    payload = await client.start(app_id=1, code="demo")
    assert payload["data"]["game_info"]["game_id"] == "g1"
```

- [ ] **Step 3: 运行测试确认失败**

Run: `pytest tests/test_signature.py tests/test_http_client.py -v`

Expected: FAIL，提示签名函数或客户端类不存在。

- [ ] **Step 4: 实现签名模块**

```python
def build_canonical_headers(*, access_key_id: str, content_md5: str, nonce: str, timestamp: int) -> str:
    return "\n".join(
        [
            f"x-bili-accesskeyid:{access_key_id}",
            f"x-bili-content-md5:{content_md5}",
            "x-bili-signature-method:HMAC-SHA256",
            f"x-bili-signature-nonce:{nonce}",
            "x-bili-signature-version:1.0",
            f"x-bili-timestamp:{timestamp}",
        ]
    )
```

- [ ] **Step 5: 实现 HTTP 客户端**

```python
class BilibiliOpenClient:
    async def start(self, *, app_id: int, code: str) -> dict:
        return await self._post("/v2/app/start", {"code": code, "app_id": app_id})

    async def heartbeat(self, *, game_id: str) -> dict:
        return await self._post("/v2/app/heartbeat", {"game_id": game_id})

    async def end(self, *, app_id: int, game_id: str) -> dict:
        return await self._post("/v2/app/end", {"app_id": app_id, "game_id": game_id})
```

- [ ] **Step 6: 为错误码保留原样抛出**

```python
if payload["code"] != 0:
    raise BilibiliApiError(payload["code"], payload["message"], payload.get("request_id"))
```

- [ ] **Step 7: 运行测试确认通过**

Run: `pytest tests/test_signature.py tests/test_http_client.py -v`

Expected: PASS

- [ ] **Step 8: 提交当前阶段**

```bash
git add app/bilibili/__init__.py app/bilibili/signature.py app/bilibili/http_client.py tests/test_signature.py tests/test_http_client.py
git commit -m "feat(开放平台接入): 新增签名与 start heartbeat end HTTP 客户端"
```

## Task 3: 实现 WebSocket 协议编解码与事件解析

**Files:**
- Create: `app/bilibili/ws_protocol.py`
- Modify: `app/models.py`
- Create: `tests/test_ws_protocol.py`

- [ ] **Step 1: 先写协议解析测试**

```python
from app.bilibili.ws_protocol import encode_packet, decode_packets, OP_AUTH


def test_encode_packet_sets_expected_operation():
    packet = encode_packet(operation=OP_AUTH, body='{"key":"value"}'.encode())
    assert len(packet) > 16
```

- [ ] **Step 2: 先写压缩包解析测试**

```python
import zlib

from app.bilibili.ws_protocol import encode_packet, decode_packets, OP_SEND_SMS_REPLY


def test_decode_packets_handles_zlib_payload():
    inner = encode_packet(operation=OP_SEND_SMS_REPLY, body=b'{"cmd":"LIVE_OPEN_PLATFORM_LIKE","data":{}}')
    outer = encode_packet(operation=OP_SEND_SMS_REPLY, body=zlib.compress(inner), version=2)
    packets = decode_packets(outer)
    assert packets[0].body == b'{"cmd":"LIVE_OPEN_PLATFORM_LIKE","data":{}}'
```

- [ ] **Step 3: 运行测试确认失败**

Run: `pytest tests/test_ws_protocol.py -v`

Expected: FAIL，提示协议模块未实现。

- [ ] **Step 4: 实现协议头常量与打包解包**

```python
HEADER_LENGTH = 16
OP_HEARTBEAT = 2
OP_HEARTBEAT_REPLY = 3
OP_SEND_SMS_REPLY = 5
OP_AUTH = 7
OP_AUTH_REPLY = 8
```

- [ ] **Step 5: 实现压缩包递归解析**

```python
if version == 2:
    decompressed = zlib.decompress(body)
    packets.extend(decode_packets(decompressed))
    continue
```

- [ ] **Step 6: 在 `app/models.py` 中补标准化事件结构**

```python
class EventType(str, Enum):
    GIFT = "gift"
    DANMAKU = "danmaku"
    LIKE = "like"


class LiveEvent(BaseModel):
    event_type: EventType
    cmd: str
    room_id: int
    open_id: str
    uname: str
    timestamp: int
    payload: dict
```

- [ ] **Step 7: 实现原始 `cmd` 到标准事件的解析函数**

```python
def parse_event_message(message: dict) -> LiveEvent | None:
    cmd = message.get("cmd")
    if cmd == "LIVE_OPEN_PLATFORM_SEND_GIFT":
        ...
    if cmd == "LIVE_OPEN_PLATFORM_DM":
        ...
    if cmd == "LIVE_OPEN_PLATFORM_LIKE":
        ...
    return None
```

- [ ] **Step 8: 再次运行测试确认通过**

Run: `pytest tests/test_ws_protocol.py -v`

Expected: PASS

- [ ] **Step 9: 提交当前阶段**

```bash
git add app/bilibili/ws_protocol.py app/models.py tests/test_ws_protocol.py
git commit -m "feat(长连协议): 完成官方 WebSocket 协议解析与事件标准化"
```

## Task 4: 实现单直播间会话、双心跳与自动重连

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/event_hub.py`
- Create: `app/services/live_session.py`
- Create: `app/bilibili/ws_client.py`
- Create: `tests/test_event_hub.py`
- Create: `tests/test_live_session.py`

- [ ] **Step 1: 先写事件中心测试**

```python
from app.services.event_hub import EventHub


def test_event_hub_keeps_recent_events_only():
    hub = EventHub(max_events=2)
    hub.publish({"id": 1})
    hub.publish({"id": 2})
    hub.publish({"id": 3})
    assert hub.snapshot() == [{"id": 2}, {"id": 3}]
```

- [ ] **Step 2: 先写会话服务状态测试**

```python
import pytest

from app.services.live_session import LiveSessionService, SessionStatus


@pytest.mark.asyncio
async def test_stop_without_running_session_keeps_idle(fake_dependencies):
    service = LiveSessionService(**fake_dependencies)
    await service.stop()
    assert service.status == SessionStatus.IDLE
```

- [ ] **Step 3: 运行测试确认失败**

Run: `pytest tests/test_event_hub.py tests/test_live_session.py -v`

Expected: FAIL

- [ ] **Step 4: 实现 `EventHub`**

```python
class EventHub:
    def __init__(self, max_events: int = 200) -> None:
        self._events: deque[dict] = deque(maxlen=max_events)
        self._subscribers: set[asyncio.Queue] = set()
```

- [ ] **Step 5: 实现 `BilibiliWsClient`**

```python
class BilibiliWsClient:
    async def connect_and_consume(self, *, wss_links: list[str], auth_body: str, on_event):
        ...
```

要求：

- 连接成功后先发 `OP_AUTH`
- 每 20 秒发一次 `OP_HEARTBEAT`
- 每收到 `cmd` 事件后调用 `on_event`

- [ ] **Step 6: 实现 `LiveSessionService.start()`**

```python
async def start(self, *, code: str) -> None:
    self.status = SessionStatus.STARTING
    start_payload = await self.api_client.start(app_id=self.settings.app_id, code=code)
    ...
```

- [ ] **Step 7: 实现项目心跳后台任务**

```python
async def _heartbeat_loop(self) -> None:
    while self.status == SessionStatus.RUNNING:
        await self.api_client.heartbeat(game_id=self.game_id)
        await asyncio.sleep(20)
```

- [ ] **Step 8: 实现自动重连**

```python
async def _handle_ws_disconnect(self) -> None:
    self.status = SessionStatus.RECONNECTING
    ...
```

约束：

- 收到 `LIVE_OPEN_PLATFORM_INTERACTION_END` 时直接终止当前会话，不走普通重连
- 项目心跳返回 `7003` 时直接转入错误并提示重新启动

- [ ] **Step 9: 实现 `stop()` 优雅停止逻辑**

```python
async def stop(self) -> None:
    self.status = SessionStatus.STOPPING
    ...
    await self.api_client.end(app_id=self.settings.app_id, game_id=self.game_id)
```

- [ ] **Step 10: 运行测试确认通过**

Run: `pytest tests/test_event_hub.py tests/test_live_session.py -v`

Expected: PASS

- [ ] **Step 11: 提交当前阶段**

```bash
git add app/services/__init__.py app/services/event_hub.py app/services/live_session.py app/bilibili/ws_client.py tests/test_event_hub.py tests/test_live_session.py
git commit -m "feat(会话管理): 支持单直播间会话 双心跳 自动重连与优雅停止"
```

## Task 5: 实现 FastAPI 路由、本地 Web 面板与 SSE 推送

**Files:**
- Create: `app/api/routes.py`
- Create: `app/templates/index.html`
- Create: `app/static/app.js`
- Create: `app/static/style.css`
- Modify: `app/main.py`
- Create: `tests/test_api_routes.py`

- [ ] **Step 1: 先写接口测试**

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_status_endpoint_returns_idle_state():
    client = TestClient(create_app())
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["status"] == "idle"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_api_routes.py -v`

Expected: FAIL，提示路由或工厂函数不存在。

- [ ] **Step 3: 实现应用工厂与路由注册**

```python
def create_app() -> FastAPI:
    app = FastAPI(title="Bilibili Live Interaction")
    ...
    return app
```

- [ ] **Step 4: 实现本地接口**

需要提供：

- `GET /`
- `GET /api/status`
- `POST /api/session/start`
- `POST /api/session/stop`
- `GET /api/events/stream`

- [ ] **Step 5: 用 SSE 推送事件**

```python
async def event_stream():
    queue = event_hub.subscribe()
    try:
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    finally:
        event_hub.unsubscribe(queue)
```

- [ ] **Step 6: 实现页面结构**

页面至少包含：

- 配置状态提示
- 主播身份码输入框
- 启动按钮
- 停止按钮
- 状态卡片
- 礼物、弹幕、点赞三栏事件流

- [ ] **Step 7: 实现前端交互**

```javascript
const source = new EventSource("/api/events/stream");
source.onmessage = (event) => {
  const payload = JSON.parse(event.data);
  renderEvent(payload);
};
```

- [ ] **Step 8: 实现基础样式**

要求：

- 状态区域醒目
- 礼物卡片高亮价值信息
- 三类事件清晰分组
- 面板在桌面宽度下可直接使用

- [ ] **Step 9: 运行测试确认通过**

Run: `pytest tests/test_api_routes.py -v`

Expected: PASS

- [ ] **Step 10: 提交当前阶段**

```bash
git add app/api/routes.py app/templates/index.html app/static/app.js app/static/style.css app/main.py tests/test_api_routes.py
git commit -m "feat(本地面板): 新增 FastAPI 路由 SSE 实时推送与可视化页面"
```

## Task 6: 补文档、日志目录与全量验证

**Files:**
- Create: `logs/.gitkeep`
- Create: `README.md`
- Modify: `.env.example`
- Modify: `requirements.txt`

- [ ] **Step 1: 创建日志目录占位文件**

```text
logs/.gitkeep
```

- [ ] **Step 2: 编写运行说明**

`README.md` 需包含：

- 环境要求
- 安装依赖命令
- `.env` 配置说明
- 启动服务命令
- 页面访问地址
- 联调步骤
- 常见错误码说明

- [ ] **Step 3: 校验依赖完整性**

确保 `requirements.txt` 至少包含：

```text
fastapi
uvicorn
httpx
websockets
python-dotenv
pydantic
pytest
```

- [ ] **Step 4: 运行全量测试**

Run: `pytest -v`

Expected: 全部 PASS

- [ ] **Step 5: 本地启动验证**

Run: `uvicorn app.main:app --reload`

Expected:

- 服务成功启动
- 控制台无导入错误
- 浏览器可访问 `http://127.0.0.1:8000`

- [ ] **Step 6: 真实联调检查清单**

使用真实 `.env` 后执行：

1. 打开页面
2. 输入主播身份码 `code`
3. 点击启动监听
4. 确认成功显示主播信息和房间号
5. 人工发送弹幕、点赞、礼物
6. 确认页面实时出现三类事件
7. 点击停止监听
8. 确认服务停止并释放当前会话

- [ ] **Step 7: 提交当前阶段**

```bash
git add logs/.gitkeep README.md .env.example requirements.txt
git commit -m "docs(运行说明): 补充联调文档 日志目录与本地运行指引"
```

## Completion Checklist

- [ ] 配置加载与校验已完成
- [ ] 官方签名与 HTTP API 已完成
- [ ] WebSocket 协议解析已完成
- [ ] 单直播间会话与双心跳已完成
- [ ] 自动重连与异常停止已完成
- [ ] 本地 Web 面板已完成
- [ ] SSE 实时事件推送已完成
- [ ] 单元测试与接口测试通过
- [ ] 真实联调通过

## Notes

- 当前工作区不是 `git` 仓库，上面的 `git add / git commit` 命令是执行模板；如果后续在正式仓库中实施，请直接沿用这些提交粒度和提交信息风格。
- 当前会话尚未获得子代理授权，因此该计划未执行子代理评审；实施阶段如你选择“Subagent-Driven”，再进入对应流程。
