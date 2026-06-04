# Blive_DGLAB 功能差距收敛 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以第三方房间消息流为主链路，补齐类似 `Blive_DGLAB` 的核心玩法，包括区分舰长/提督/总督弹幕、按用户限流、SC/上舰独立事件、互动事件、控制日志流和更完整的 OBS 展示。

**Architecture:** 继续沿用当前“第三方事件标准化 -> 会话服务 -> IM/蓝牙输出 -> Web UI”的主链路，把现有 `gift / danmaku / like` 扩成更细的第三方事件模型，并把舰队等级、用户限流和规则过滤放到统一调度层。蓝牙规则继续作为主要输出通道，IM 指令侧复用现有命令派发能力；官方 `open-live` 只保持不破坏，不作为本轮主实现目标。

**Tech Stack:** Python 3.11+、FastAPI、Pydantic、原生 JavaScript、Jinja2、pytest、SSE

---

## 文件结构与职责

**事件接入与标准化**
- Modify: `app/third_party/event_mapper.py`
- Modify: `app/third_party/ws_client.py`

**会话与调度**
- Modify: `app/services/third_party_session.py`
- Modify: `app/services/live_session_manager.py`
- Modify: `app/services/danmaku_dispatcher.py`
- Modify: `app/services/gift_dispatcher.py`
- Modify: `app/services/event_hub.py`
- Modify: `app/services/command_session.py`

**蓝牙规则与输出**
- Modify: `app/bluetooth/models.py`
- Modify: `app/bluetooth/dispatcher.py`
- Modify: `app/bluetooth/service.py`
- Modify: `app/bluetooth/storage.py`

**前端与页面**
- Modify: `app/api/routes.py`
- Modify: `app/templates/index.html`
- Modify: `app/templates/bluetooth_overlay.html`
- Modify: `app/static/app.js`
- Modify: `app/static/bluetooth_overlay.js`
- Modify: `app/static/bluetooth_studio.js`
- Modify: `app/static/style.css`

**测试**
- Modify: `tests/test_third_party_mapper.py`
- Modify: `tests/test_third_party_ws_client.py`
- Modify: `tests/test_third_party_session.py`
- Modify: `tests/test_live_session_manager.py`
- Modify: `tests/test_gift_dispatcher.py`
- Modify: `tests/test_bluetooth_dispatcher.py`
- Modify: `tests/test_bluetooth_storage.py`
- Modify: `tests/test_api_routes.py`
- Modify: `tests/test_event_hub.py`
- Modify: `tests/test_frontend_assets.py`

## 优先级

### `P0`
- 区分舰长/提督/总督弹幕
- 按用户限流
- SC / 上舰 / 续费独立事件类型
- 独立控制日志流

### `P1`
- 互动事件：进房、关注、分享、特别关注
- OBS 演出页增强
- 规则中心支持更多过滤条件

### `P2`
- 可选控制后端抽象，兼容外部 DG-Lab Hub / HTTP 控制器

## 实际开发顺序

### 第一阶段：先把第三方弹幕“识别对”

目标：先让第三方链路正确区分普通用户、舰长、提督、总督，并把用户身份字段带出来。

只做这些文件：
- `app/third_party/event_mapper.py`
- `tests/test_third_party_mapper.py`

完成标准：
- `DANMU_MSG` 能输出 `uid`
- `DANMU_MSG` 能输出 `guard_level`
- `DANMU_MSG` 能输出 `guard_label`
- 现有第三方弹幕事件结构不回退

建议先跑：

```bash
pytest tests/test_third_party_mapper.py -v
```

### 第二阶段：把第三方 SC / 上舰 / 续费拆成独立事件

目标：不要再把这三类事件混成普通礼物，给后面的规则系统留出独立入口。

只做这些文件：
- `app/third_party/event_mapper.py`
- `app/services/third_party_session.py`
- `tests/test_third_party_mapper.py`
- `tests/test_third_party_session.py`

完成标准：
- `SUPER_CHAT_MESSAGE -> super_chat`
- `GUARD_BUY -> guard_buy`
- `USER_TOAST_MSG -> guard_renew` 或统一成 `guard_buy` 的续费子类型
- 会话层能把这些新事件继续送进蓝牙/IM 输出链路

建议接着跑：

```bash
pytest tests/test_third_party_mapper.py tests/test_third_party_session.py -v
```

### 第三阶段：把弹幕规则从“全局冷却”升级成“按用户限流 + 按舰队等级过滤”

目标：做出最接近 `Blive_DGLAB` 的真实玩法。

只做这些文件：
- `app/services/danmaku_dispatcher.py`
- `app/bluetooth/dispatcher.py`
- `tests/test_gift_dispatcher.py`
- `tests/test_bluetooth_dispatcher.py`

完成标准：
- 同一用户在窗口期内超过次数上限后不再触发
- 可以配置最低舰队等级
- 可以按舰队等级做额外加成
- 默认规则不影响未配置用户

建议再跑：

```bash
pytest tests/test_gift_dispatcher.py tests/test_bluetooth_dispatcher.py -v
```

### 这 3 步做完后的结果

- 第三方链路已经能区分 `舰长 / 提督 / 总督` 弹幕
- SC、上舰、续费已经不是“伪礼物”
- 弹幕触发已经具备按用户和按身份控制的基础
- 这时再做控制日志流和 OBS 增强，收益最高

### 第四阶段：补齐 IM 规则中心与页面化价格配置

目标：让 IM 指令链路不再依赖手改 `gift_command_mappings.json`，并支持第三方独立事件与舰队等级弹幕分流。

只做这些文件：
- `app/command_gateway/mapping.py`
- `app/services/command_rule_service.py`
- `app/services/danmaku_dispatcher.py`
- `app/services/gift_dispatcher.py`
- `app/api/routes.py`
- `app/main.py`
- `app/templates/index.html`
- `app/templates/command_studio.html`
- `app/static/command_studio.js`
- `tests/test_gift_mapping.py`
- `tests/test_gift_dispatcher.py`
- `tests/test_api_routes.py`
- `tests/test_frontend_assets.py`

完成标准：
- `gift / super_chat / guard_buy / guard_renew` 支持独立价格区间映射
- 弹幕支持按 `普通 / 舰长 / 提督 / 总督` 分配不同 IM 指令槽位
- 页面可直接编辑礼物价格区间、点赞规则和弹幕舰队槽位映射
- 保存后无需重启即可让当前 IM 调度使用新规则

## 实施原则

1. 先补第三方事件模型和测试，再改规则和前端。
2. 先打通 `P0`，只要 `P0` 完成，整体体验就已经接近目标项目。
3. 舰队等级一律统一输出为 `guard_level` 和 `guard_label`，避免前后端重复判定。
4. 用户限流统一按“来源 + 房间 + 用户 + 规则”记账，不能只做全局冷却。
5. 规则中心优先复用现有蓝牙规则页，不新开一套后台。

### Task 1: 建立第三方事件扩展模型与舰队等级测试

**Files:**
- Modify: `tests/test_third_party_mapper.py`
- Modify: `app/third_party/event_mapper.py`

- [x] **Step 1: 为第三方弹幕补舰队等级标准化失败测试**

```python
def test_map_danmaku_msg_with_guard_level() -> None:
    event = map_third_party_message(message, room_id=123)
    assert event["payload"]["guard_level"] == 1
    assert event["payload"]["guard_label"] == "舰长"
```

- [x] **Step 2: 为第三方弹幕补用户身份字段失败测试**

```python
assert event["open_id"] == ""
assert event["payload"]["uid"] == 123456
```

- [x] **Step 3: 运行映射测试确认失败**

Run: `pytest tests/test_third_party_mapper.py -v`
Expected: FAIL，提示缺少 `guard_label`、`uid` 或第三方弹幕未解析舰队等级

- [x] **Step 4: 在第三方弹幕标准化中加入舰队等级与用户字段**

```python
payload["guard_level"] = normalized_guard_level
payload["guard_label"] = guard_level_to_label(normalized_guard_level)
```

- [x] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_third_party_mapper.py -v`
Expected: PASS

- [x] **Step 6: Commit**

```bash
git add tests/test_third_party_mapper.py app/third_party/event_mapper.py
git commit -m "feat(third-party-events): 统一舰队等级字段并支持舰长提督总督弹幕区分"
```

### Task 2: 把 SC / 上舰 / 续费从 gift 中拆成独立事件类型

**Files:**
- Modify: `tests/test_third_party_mapper.py`
- Modify: `tests/test_third_party_session.py`
- Modify: `app/third_party/event_mapper.py`
- Modify: `app/services/third_party_session.py`

- [x] **Step 1: 为 `SUPER_CHAT_MESSAGE` 写独立事件类型失败测试**

```python
assert event["event_type"] == "super_chat"
assert event["payload"]["price"] == 30
```

- [x] **Step 2: 为 `GUARD_BUY` 和 `USER_TOAST_MSG` 写失败测试**

```python
assert event["event_type"] == "guard_buy"
assert event["payload"]["guard_level"] == 1
```

- [x] **Step 3: 运行映射与会话测试确认失败**

Run: `pytest tests/test_third_party_mapper.py tests/test_third_party_session.py -v`
Expected: FAIL，说明第三方会话层仍只识别 `gift / like / danmaku`

- [x] **Step 4: 在 mapper 中拆分事件类型**

```python
return {"event_type": "super_chat", ...}
```

- [x] **Step 5: 在第三方会话层把新事件交给 IM/蓝牙规则通道**

```python
elif event.get("event_type") == "super_chat":
    ...
```

- [x] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_third_party_mapper.py tests/test_third_party_session.py -v`
Expected: PASS

- [x] **Step 7: Commit**

```bash
git add tests/test_third_party_mapper.py tests/test_third_party_session.py app/third_party/event_mapper.py app/services/third_party_session.py
git commit -m "feat(third-party-events): 拆分醒目留言与上舰续费独立事件类型"
```

### Task 3: 实现按用户限流与舰队等级过滤/加成

**Files:**
- Modify: `tests/test_gift_dispatcher.py`
- Modify: `tests/test_bluetooth_dispatcher.py`
- Modify: `app/services/danmaku_dispatcher.py`
- Modify: `app/bluetooth/dispatcher.py`
- Modify: `app/services/live_session_manager.py`

- [x] **Step 1: 为“同一用户 N 分钟最多触发 X 次”写失败测试**

```python
def test_danmaku_dispatcher_limits_same_user_within_window() -> None:
    ...
    assert third_result["trigger_count"] == 0
```

- [x] **Step 2: 为“仅舰长以上可触发”写失败测试**

```python
assert result["message"] == "当前用户舰队等级不足"
```

- [x] **Step 3: 为“总督获得额外强度/次数加成”写失败测试**

```python
assert result["trigger_count"] == 2
```

- [x] **Step 4: 运行调度测试确认失败**

Run: `pytest tests/test_gift_dispatcher.py tests/test_bluetooth_dispatcher.py -v`
Expected: FAIL，说明当前仍是房间级冷却，不区分用户和舰队等级

- [x] **Step 5: 在弹幕调度器中增加用户维度限流键**

```python
cooldown_key = (source, room_id, uid_or_open_id, command_id)
```

- [x] **Step 6: 在蓝牙调度器中增加最低舰队等级与倍率/偏移处理**

```python
if guard_level < min_guard_level:
    return blocked_result
```

- [x] **Step 7: 在 manager 中暴露新运行参数的默认值**

```python
payload["danmaku_user_limit_window_seconds"] = ...
```

- [x] **Step 8: 运行测试确认通过**

Run: `pytest tests/test_gift_dispatcher.py tests/test_bluetooth_dispatcher.py -v`
Expected: PASS

- [x] **Step 9: Commit**

```bash
git add tests/test_gift_dispatcher.py tests/test_bluetooth_dispatcher.py app/services/danmaku_dispatcher.py app/bluetooth/dispatcher.py app/services/live_session_manager.py
git commit -m "feat(danmaku-rules): 支持按用户限流与舰队等级过滤加成"
```

### Task 4: 扩展蓝牙规则模型，支持新事件类型和舰队等级条件

**Files:**
- Modify: `tests/test_bluetooth_storage.py`
- Modify: `tests/test_bluetooth_dispatcher.py`
- Modify: `app/bluetooth/models.py`
- Modify: `app/bluetooth/storage.py`
- Modify: `app/bluetooth/dispatcher.py`

- [x] **Step 1: 为默认规则结构写失败测试**

```python
assert any(rule.event_type == "super_chat" for rule in payload.bluetooth_event_rules)
```

- [x] **Step 2: 为规则过滤字段持久化写失败测试**

```python
assert rule.filters["min_guard_level"] == 2
```

- [x] **Step 3: 运行蓝牙存储与调度测试确认失败**

Run: `pytest tests/test_bluetooth_storage.py tests/test_bluetooth_dispatcher.py -v`
Expected: FAIL，说明默认规则尚未覆盖新事件或过滤字段未保存

- [x] **Step 4: 在模型默认值中加入 `super_chat / guard_buy` 规则**

```python
BluetoothEventRule(id="super-chat-default", event_type="super_chat", ...)
```

- [x] **Step 5: 在 storage 中确保新过滤字段原样保存和恢复**

```python
filters=dict(item["filters"])
```

- [x] **Step 6: 在 dispatcher 中识别新事件与最小舰队等级**

```python
if rule.event_type == "super_chat":
    ...
```

- [x] **Step 7: 运行测试确认通过**

Run: `pytest tests/test_bluetooth_storage.py tests/test_bluetooth_dispatcher.py -v`
Expected: PASS

- [x] **Step 8: Commit**

```bash
git add tests/test_bluetooth_storage.py tests/test_bluetooth_dispatcher.py app/bluetooth/models.py app/bluetooth/storage.py app/bluetooth/dispatcher.py
git commit -m "feat(bluetooth-rules): 扩展蓝牙规则支持新事件类型与舰队等级过滤"
```

### Task 5: 补独立控制日志流并把前端分成事件日志与控制日志

**Files:**
- Modify: `tests/test_event_hub.py`
- Modify: `tests/test_api_routes.py`
- Modify: `tests/test_frontend_assets.py`
- Modify: `app/services/event_hub.py`
- Modify: `app/services/command_session.py`
- Modify: `app/bluetooth/service.py`
- Modify: `app/api/routes.py`
- Modify: `app/templates/index.html`
- Modify: `app/static/app.js`

- [x] **Step 1: 为控制日志通道写失败测试**

```python
def test_event_hub_supports_control_log_stream() -> None:
    hub.publish_control({...})
    assert hub.control_snapshot()[0]["type"] == "bluetooth_trigger"
```

- [x] **Step 2: 为 API 和前端钩子写失败测试**

```python
assert 'id="control-events"' in html
assert 'new EventSource("/api/events/stream")' in js
assert '"/api/control/stream"' in js
```

- [x] **Step 3: 运行测试确认失败**

Run: `pytest tests/test_event_hub.py tests/test_api_routes.py tests/test_frontend_assets.py -v`
Expected: FAIL，说明当前没有独立控制日志流

- [x] **Step 4: 在 `EventHub` 中增加控制日志缓冲和订阅**

```python
def publish_control(self, event: dict[str, Any]) -> None:
    ...
```

- [x] **Step 5: 在命令发送和蓝牙触发成功/失败后写入控制日志**

```python
self.event_hub.publish_control({...})
```

- [x] **Step 6: 在 `routes.py` 中暴露控制日志 SSE**

```python
@router.get("/api/control/stream")
async def control_stream(...):
    ...
```

- [x] **Step 7: 在首页模板和脚本中增加控制日志区域**

```javascript
const controlSource = new EventSource("/api/control/stream");
```

- [x] **Step 8: 运行测试确认通过**

Run: `pytest tests/test_event_hub.py tests/test_api_routes.py tests/test_frontend_assets.py -v`
Expected: PASS

- [x] **Step 9: Commit**

```bash
git add tests/test_event_hub.py tests/test_api_routes.py tests/test_frontend_assets.py app/services/event_hub.py app/services/command_session.py app/bluetooth/service.py app/api/routes.py app/templates/index.html app/static/app.js
git commit -m "feat(control-log): 拆分控制日志流并接入首页监控"
```

### Task 6: 接入第三方互动事件并扩展事件规则页

**Files:**
- Modify: `tests/test_third_party_ws_client.py`
- Modify: `tests/test_third_party_mapper.py`
- Modify: `tests/test_frontend_assets.py`
- Modify: `app/third_party/ws_client.py`
- Modify: `app/third_party/event_mapper.py`
- Modify: `app/static/bluetooth_studio.js`
- Modify: `app/static/style.css`

- [x] **Step 1: 为互动事件注册写失败测试**

```python
assert "INTERACT_WORD" in registered_events
```

- [x] **Step 2: 为互动事件标准化写失败测试**

```python
assert event["event_type"] == "interact"
assert event["payload"]["interact_type"] == "follow"
```

- [x] **Step 3: 运行第三方事件测试确认失败**

Run: `pytest tests/test_third_party_ws_client.py tests/test_third_party_mapper.py -v`
Expected: FAIL，说明还未监听和标准化互动事件

- [x] **Step 4: 在 `ws_client.py` 注册第三方互动类事件**

```python
for event_name in (..., "INTERACT_WORD"):
    ...
```

- [x] **Step 5: 在 mapper 中输出 `进房 / 关注 / 分享 / 特别关注` 子类型**

```python
payload["interact_type"] = "share"
```

- [x] **Step 6: 在规则页中加入互动事件分组显示**

```javascript
group_label: "互动事件"
```

- [x] **Step 7: 运行测试确认通过**

Run: `pytest tests/test_third_party_ws_client.py tests/test_third_party_mapper.py tests/test_frontend_assets.py -v`
Expected: PASS

- [x] **Step 8: Commit**

```bash
git add tests/test_third_party_ws_client.py tests/test_third_party_mapper.py tests/test_frontend_assets.py app/third_party/ws_client.py app/third_party/event_mapper.py app/static/bluetooth_studio.js app/static/style.css
git commit -m "feat(interact-events): 支持进房关注分享等互动事件接入与配置"
```

### Task 7: 升级 OBS 页面，显示弹幕演出与触发信息

**Files:**
- Modify: `tests/test_api_routes.py`
- Modify: `tests/test_frontend_assets.py`
- Modify: `app/api/routes.py`
- Modify: `app/templates/bluetooth_overlay.html`
- Modify: `app/static/bluetooth_overlay.js`
- Modify: `app/services/event_hub.py`

- [x] **Step 1: 为 overlay 数据结构写失败测试**

```python
assert response.json()["history"][0]["msg"] == "开火"
```

- [x] **Step 2: 为前端资源钩子写失败测试**

```python
assert "overlay-danmaku-list" in overlay_html
assert "renderOverlayDanmaku" in overlay_js
```

- [x] **Step 3: 运行 API 和前端测试确认失败**

Run: `pytest tests/test_api_routes.py tests/test_frontend_assets.py -v`
Expected: FAIL，说明 overlay 仍只显示设备状态

- [x] **Step 4: 在 overlay payload 中附带最近触发事件摘要**

```python
payload["recent_events"] = [...]
```

- [x] **Step 5: 在 overlay 页面中增加弹幕/SC/上舰展示区**

```javascript
function renderOverlayDanmaku(events) {
  ...
}
```

- [x] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_api_routes.py tests/test_frontend_assets.py -v`
Expected: PASS

- [x] **Step 7: Commit**

```bash
git add tests/test_api_routes.py tests/test_frontend_assets.py app/api/routes.py app/templates/bluetooth_overlay.html app/static/bluetooth_overlay.js app/services/event_hub.py
git commit -m "feat(obs-overlay): 增强小窗展示弹幕与触发演出信息"
```

### Task 8: 全量回归与实现偏差记录

**Files:**
- Modify: `docs/superpowers/plans/2026-06-04-blivedglab-gap.md`
- Verify: `tests/test_ws_protocol.py`
- Verify: `tests/test_third_party_mapper.py`
- Verify: `tests/test_third_party_ws_client.py`
- Verify: `tests/test_live_session.py`
- Verify: `tests/test_third_party_session.py`
- Verify: `tests/test_live_session_manager.py`
- Verify: `tests/test_gift_dispatcher.py`
- Verify: `tests/test_bluetooth_dispatcher.py`
- Verify: `tests/test_bluetooth_storage.py`
- Verify: `tests/test_event_hub.py`
- Verify: `tests/test_api_routes.py`
- Verify: `tests/test_frontend_assets.py`

- [x] **Step 1: 运行 `P0` 相关后端测试**

Run: `pytest tests/test_third_party_mapper.py tests/test_third_party_session.py tests/test_gift_dispatcher.py tests/test_bluetooth_dispatcher.py -v`
Expected: PASS

- [x] **Step 2: 运行事件流与前端测试**

Run: `pytest tests/test_event_hub.py tests/test_api_routes.py tests/test_frontend_assets.py -v`
Expected: PASS

- [x] **Step 3: 运行全量测试**

Run: `pytest -v`
Expected: PASS

- [x] **Step 4: 如实现中对第三方弹幕舰队字段索引做了兼容性折中，在本计划末尾补充实际偏差**

```markdown
- 第三方 `DANMU_MSG` 的舰队等级字段按当前库版本的索引解析，如后续上游升级需复核。
```

- [x] **Step 5: 最终 Commit**

```bash
git add app tests docs/superpowers/plans/2026-06-04-blivedglab-gap.md
git commit -m "feat(blivedglab-gap): 补齐直播联动核心玩法与观测能力"
```

## 备注

- 区分 `舰长 / 提督 / 总督` 弹幕已经并入 `P0`，优先落在统一事件模型和规则过滤上。
- 本计划默认第三方链路为主，官方 `open-live` 仅要求不受本轮改动破坏，不要求同步补齐所有玩法。
- `P2` 的外部 DG-Lab Hub 兼容层不影响 `P0 / P1` 上线，可单独排期。

## 实现记录

- 2026-06-04：已补齐独立控制日志流、第三方互动事件、SC/上舰/续费/互动蓝牙规则、OBS 强度小窗最近事件展示和使用说明。
- 2026-06-04：全量回归 `python -m pytest -v`，结果 `182 passed`。
- 第三方 `INTERACT_WORD` 按 `msg_type=1/2/3` 映射为进房/关注/分享，并兼容 `msg_type=4` 为特别关注。

