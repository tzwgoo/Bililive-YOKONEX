# Bilibili 双链路直播监听集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有项目中保留官方 `open-live` 监听实现，同时新增第三方房间消息流监听模式，并通过同一页面做模式切换。

**Architecture:** 新增 `LiveSessionManager` 统一调度 `OpenLiveSessionService` 和 `ThirdPartyLiveSessionService`；前端通过 `mode/value` 统一启动；事件面板和下游指令通道保持共用。

**Tech Stack:** Python 3.12, FastAPI, asyncio, websockets, SSE, 现有前端原生 JS

---

## File Map

- `app/main.py`
  装配双模式监听服务与统一 manager。
- `app/api/routes.py`
  调整启动接口 payload，继续暴露状态、停止、事件流接口。
- `app/services/open_live_session.py`
  承接现有官方 `open-live` 监听实现。
- `app/services/third_party_session.py`
  新增第三方模式监听实现。
- `app/services/live_session_manager.py`
  统一调度不同模式监听服务。
- `app/third_party/event_mapper.py`
  将第三方原始事件转换为统一事件结构。
- `app/third_party/ws_client.py`
  第三方链路连接与原始消息接收。
- `app/services/gift_dispatcher.py`
  继续复用，只消费统一 `gift` 事件。
- `app/templates/index.html`
  增加模式选择器与动态输入文案。
- `app/static/app.js`
  切换为统一 `mode/value` 启动请求，显示来源标签。
- `tests/test_live_session_manager.py`
  覆盖 manager 调度。
- `tests/test_third_party_mapper.py`
  覆盖第三方事件适配。
- `tests/test_api_routes.py`
  扩展统一启动接口测试。
- `README.md`
  更新双模式使用说明。
- `docs/使用说明.md`
  更新页面操作说明。

## Task 1: 拆分官方实现并引入统一管理器

**Files:**
- Create: `app/services/open_live_session.py`
- Create: `app/services/live_session_manager.py`
- Modify: `app/main.py`
- Modify: `app/api/routes.py`
- Create: `tests/test_live_session_manager.py`

- [ ] **Step 1: 先写管理器调度测试**

```python
import pytest

from app.services.live_session_manager import LiveSessionManager


class FakeSession:
    def __init__(self):
        self.started_with = None
        self.stopped = False
        self.status_payload = {"status": "idle"}

    async def start(self, *, value: str):
        self.started_with = value

    async def stop(self):
        self.stopped = True

    def get_status_payload(self):
        return self.status_payload


@pytest.mark.anyio
async def test_manager_routes_open_live_start():
    open_live = FakeSession()
    third_party = FakeSession()
    manager = LiveSessionManager(open_live_session=open_live, third_party_session=third_party)

    await manager.start(mode="open_live", value="code-demo")

    assert open_live.started_with == "code-demo"
    assert third_party.started_with is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_live_session_manager.py -v`

Expected: FAIL，提示 manager 或拆分服务不存在。

- [ ] **Step 3: 拆分当前官方实现**

把现有 `LiveSessionService` 迁移为 `OpenLiveSessionService`，保持行为不变，但将启动方法统一成：

```python
async def start(self, *, value: str) -> None:
    code = value
```

- [ ] **Step 4: 实现 `LiveSessionManager`**

要求：

- 管理当前 `mode`
- 启动前校验参数
- 只允许同一时间一个活动会话
- `get_status_payload()` 自动附带 `mode`

- [ ] **Step 5: 调整路由启动接口**

请求体改为：

```json
{
  "mode": "open_live",
  "value": "code-demo"
}
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_live_session_manager.py tests/test_api_routes.py -v`

Expected: PASS

## Task 2: 新增第三方事件适配与监听服务骨架

**Files:**
- Create: `app/third_party/__init__.py`
- Create: `app/third_party/event_mapper.py`
- Create: `app/services/third_party_session.py`
- Create: `tests/test_third_party_mapper.py`

- [ ] **Step 1: 先写事件映射测试**

```python
from app.third_party.event_mapper import map_third_party_message


def test_map_send_gift_to_standard_gift_event():
    message = {
        "cmd": "SEND_GIFT",
        "data": {
            "giftId": 1,
            "giftName": "辣条",
            "num": 1,
            "uname": "用户A",
            "price": 100,
            "timestamp": 1714113037,
        },
    }

    event = map_third_party_message(message, room_id=123)

    assert event["event_type"] == "gift"
    assert event["source"] == "third_party_ws"
    assert event["payload"]["gift_name"] == "辣条"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_third_party_mapper.py -v`

Expected: FAIL

- [ ] **Step 3: 实现第三方事件映射器**

至少覆盖：

- `DANMU_MSG`
- `SEND_GIFT`
- `LIKE_INFO_V3_CLICK` / `LIKE_INFO_V3_UPDATE`

- [ ] **Step 4: 实现第三方会话服务骨架**

先不接真实库，先实现：

- `start(value=room_id)`
- `stop()`
- `get_status_payload()`

使其能被 manager 正常调度。

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_third_party_mapper.py tests/test_live_session_manager.py -v`

Expected: PASS

## Task 3: 接入真实第三方房间消息流

**Files:**
- Modify: `requirements.txt`
- Create: `app/third_party/ws_client.py`
- Modify: `app/services/third_party_session.py`

- [ ] **Step 1: 增加第三方依赖**

将 `bilibili-api` 加入依赖清单。

- [ ] **Step 2: 封装第三方监听客户端**

提供一个统一适配层，负责：

- 根据 `room_id` 建立连接
- 接收原始房间消息
- 回调给 `event_mapper`

- [ ] **Step 3: 将适配后的事件推入 `EventHub`**

输出结构必须与官方模式一致，只新增：

- `source = third_party_ws`

- [ ] **Step 4: 加入第三方断线恢复**

状态至少覆盖：

- `starting`
- `running`
- `reconnecting`
- `stopping`
- `error`

- [ ] **Step 5: 验证第三方礼物事件能继续触发命令派发**

Run: `pytest tests/test_gift_dispatcher.py tests/test_third_party_mapper.py -v`

Expected: PASS

## Task 4: 更新前端为模式切换

**Files:**
- Modify: `app/templates/index.html`
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`
- Create: `tests/test_frontend_assets.py`

- [ ] **Step 1: 先写前端静态回归测试**

验证页面和脚本中出现：

- `session-mode`
- `open_live`
- `third_party`

- [ ] **Step 2: 页面增加模式切换控件**

要求：

- 单选或下拉均可
- 显示当前输入标签
- 根据模式显示 `code` 或 `room_id`

- [ ] **Step 3: 启动请求改为统一结构**

前端提交：

```json
{
  "mode": "...",
  "value": "..."
}
```

- [ ] **Step 4: 事件卡片增加来源标签**

礼物、弹幕、点赞卡片可显示：

- `官方`
- `第三方`

- [ ] **Step 5: 再次运行前端相关测试**

Run: `pytest tests/test_frontend_assets.py tests/test_api_routes.py -v`

Expected: PASS

## Task 5: 更新文档与回归验证

**Files:**
- Modify: `README.md`
- Modify: `docs/使用说明.md`

- [ ] **Step 1: 文档补充双模式说明**

内容包括：

- 官方模式怎么用
- 第三方模式怎么用
- 两种模式的输入区别
- 下游指令通道登录方式不变

- [ ] **Step 2: 跑全量测试**

Run: `pytest -v`

Expected: 全部 PASS

- [ ] **Step 3: 本地页面验证**

检查：

- 模式切换能改变输入提示
- 官方模式仍能展示原有状态
- 第三方模式能提交 `room_id`

## Completion Checklist

- [ ] 官方 `open-live` 模式保留可用
- [ ] 第三方模式可按 `room_id` 启动
- [ ] 页面支持模式切换
- [ ] 统一事件结构增加 `source`
- [ ] 礼物映射与下游指令发送继续可用
- [ ] 文档已更新
- [ ] 全量测试通过

## Notes

- 当前目录不是 `git` 仓库，因此本计划不包含实际提交动作。
- 第三方模式的真实接入优先以 `Nemo2011/bilibili-api` 的 `LiveDanmaku` 思路为准；如运行时存在版本兼容问题，再做一层本地兼容适配。
