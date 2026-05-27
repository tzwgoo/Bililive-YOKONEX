# Bilibili 控制台 EMS 蓝牙接入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在当前直播互动控制台中加入后端驱动的 EMS 蓝牙连接、波形库和事件绑定能力，并保持现有监听与指令通道稳定可用。

**Architecture:** 新增 `app/bluetooth/` 子系统承载配置、运行时状态、设备扫描连接和波形执行；在现有 `open_live_session` / `third_party_session` 的事件派发节点并行接入蓝牙规则分发；前端在同一控制台中扩展蓝牙状态、波形库和规则面板。

**Tech Stack:** Python 3.12, FastAPI, asyncio, Pydantic, 原生 JS, Pytest, Windows BLE 适配层

---

## File Map

- `app/bluetooth/models.py`
  定义蓝牙配置、设备摘要、波形、波形步骤、规则和运行时状态模型。
- `app/bluetooth/storage.py`
  负责 `config/bluetooth_settings.json` 的读写、默认值和 normalize。
- `app/bluetooth/runtime/base.py`
  约束 BLE 运行时接口，便于测试时注入 fake runtime。
- `app/bluetooth/runtime/memory_runtime.py`
  首阶段用内存假运行时承载扫描、连接、断开和状态切换。
- `app/bluetooth/service.py`
  聚合配置存储与运行时，向 API 和后续 dispatcher 暴露统一服务。
- `app/bluetooth/dispatcher.py`
  根据直播事件与规则触发目标波形。
- `app/api/routes.py`
  新增蓝牙状态、扫描、连接、断开、波形库和规则接口。
- `app/main.py`
  装配蓝牙服务并挂载到 `app.state`。
- `app/static/app.js`
  请求蓝牙接口并刷新蓝牙区块。
- `app/templates/index.html`
  新增 `EMS 蓝牙连接`、`EMS 波形库`、`蓝牙事件绑定` 面板骨架。
- `app/static/style.css`
  补充蓝牙卡片样式。
- `tests/test_bluetooth_storage.py`
  覆盖默认配置、normalize 和文件读写。
- `tests/test_bluetooth_service.py`
  覆盖状态、扫描、连接、断开和运行时行为。
- `tests/test_bluetooth_api.py`
  覆盖蓝牙接口。
- `tests/test_frontend_assets.py`
  追加蓝牙前端骨架断言。
- `requirements.txt`
  后续接入真实 BLE 时加入依赖。
- `build_exe.ps1`
  后续真实 BLE 依赖落地后补打包兼容。

## Task 1: 蓝牙配置与模型基础

**Files:**
- Create: `app/bluetooth/__init__.py`
- Create: `app/bluetooth/models.py`
- Create: `app/bluetooth/storage.py`
- Test: `tests/test_bluetooth_storage.py`

- [ ] **Step 1: 写默认配置加载失败测试**

```python
from app.bluetooth.storage import BluetoothSettingsStore


def test_store_returns_default_payload_when_file_missing(tmp_path):
    store = BluetoothSettingsStore(tmp_path / "bluetooth.json")

    payload = store.load()

    assert payload.bluetooth_settings.enabled is False
    assert payload.ems_waveforms
    assert payload.bluetooth_event_rules
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest --basetemp .pytest_temp tests/test_bluetooth_storage.py -q`
Expected: FAIL，提示蓝牙存储模块不存在。

- [ ] **Step 3: 写最小模型与默认值实现**

要求：

- 默认包含一个保底 EMS 波形
- 默认包含礼物、点赞、弹幕三类规则
- 支持从缺失文件回退到默认配置

- [ ] **Step 4: 再跑测试确认通过**

Run: `pytest --basetemp .pytest_temp tests/test_bluetooth_storage.py -q`
Expected: PASS

## Task 2: 蓝牙服务与假运行时

**Files:**
- Create: `app/bluetooth/runtime/base.py`
- Create: `app/bluetooth/runtime/memory_runtime.py`
- Create: `app/bluetooth/service.py`
- Test: `tests/test_bluetooth_service.py`

- [ ] **Step 1: 先写状态与连接测试**

```python
import pytest

from app.bluetooth.service import BluetoothService


@pytest.mark.anyio
async def test_service_can_scan_connect_and_disconnect(tmp_path):
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    scanned = await service.scan()
    connected = await service.connect(scanned[0].device_id)
    disconnected = await service.disconnect()

    assert scanned
    assert connected.connected is True
    assert disconnected.connected is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest --basetemp .pytest_temp tests/test_bluetooth_service.py -q`
Expected: FAIL

- [ ] **Step 3: 实现 fake runtime 与统一 service**

要求：

- `scan()` 返回受支持 EMS 测试设备列表
- `connect(device_id)` 切换当前连接设备
- `disconnect()` 清空当前连接状态
- `get_status_payload()` 输出前端可直接消费的数据

- [ ] **Step 4: 再跑测试确认通过**

Run: `pytest --basetemp .pytest_temp tests/test_bluetooth_service.py -q`
Expected: PASS

## Task 3: 蓝牙 API 与应用装配

**Files:**
- Modify: `app/api/routes.py`
- Modify: `app/main.py`
- Test: `tests/test_bluetooth_api.py`

- [ ] **Step 1: 先写蓝牙接口测试**

覆盖：

- `GET /api/bluetooth/status`
- `POST /api/bluetooth/scan`
- `POST /api/bluetooth/connect`
- `POST /api/bluetooth/disconnect`

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest --basetemp .pytest_temp tests/test_bluetooth_api.py -q`
Expected: FAIL，提示接口不存在。

- [ ] **Step 3: 增加蓝牙 service 装配和接口实现**

要求：

- `app.state.bluetooth_service` 可用
- 接口统一返回 `{ "success": True, ... }`
- 连接未知设备时返回 `400`

- [ ] **Step 4: 再跑测试确认通过**

Run: `pytest --basetemp .pytest_temp tests/test_bluetooth_api.py -q`
Expected: PASS

## Task 4: 控制台蓝牙面板骨架

**Files:**
- Modify: `app/templates/index.html`
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`
- Modify: `tests/test_frontend_assets.py`

- [ ] **Step 1: 先写前端资产测试**

断言页面包含：

- `bluetooth-status-pill`
- `bluetooth-scan-btn`
- `bluetooth-devices`
- `bluetooth-waveforms`
- `bluetooth-rules`

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest --basetemp .pytest_temp tests/test_frontend_assets.py -q`
Expected: FAIL

- [ ] **Step 3: 实现蓝牙面板骨架和状态刷新**

要求：

- 页面新增三个蓝牙卡片
- JS 新增 `refreshBluetoothStatus()`
- 扫描 / 连接 / 断开按钮可打到后端接口

- [ ] **Step 4: 再跑测试确认通过**

Run: `pytest --basetemp .pytest_temp tests/test_frontend_assets.py -q`
Expected: PASS

## Task 5: 事件规则与波形触发最小闭环

**Files:**
- Create: `app/bluetooth/dispatcher.py`
- Modify: `app/services/open_live_session.py`
- Modify: `app/services/third_party_session.py`
- Test: `tests/test_bluetooth_dispatcher.py`

- [ ] **Step 1: 先写规则命中测试**

覆盖：

- 礼物事件命中礼物规则后标记触发波形
- 点赞事件命中点赞规则后标记触发波形
- 弹幕事件命中关键词规则后标记触发波形

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest --basetemp .pytest_temp tests/test_bluetooth_dispatcher.py -q`
Expected: FAIL

- [ ] **Step 3: 实现最小 dispatcher**

要求：

- 先不发真实 BLE 包
- 只调用 `BluetoothService.trigger_waveform(...)`
- 失败不阻断原有命令派发

- [ ] **Step 4: 将 dispatcher 挂到两个 session 的事件处理节点**

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest --basetemp .pytest_temp tests/test_bluetooth_dispatcher.py tests/test_live_session.py tests/test_third_party_session.py -q`
Expected: PASS

## Task 6: 真实 BLE 运行时接入

**Files:**
- Modify: `requirements.txt`
- Create: `app/bluetooth/runtime/bleak_runtime.py`
- Modify: `app/bluetooth/service.py`
- Modify: `build_exe.ps1`

- [ ] **Step 1: 在可替换 runtime 基础上补真实 BLE runtime 测试桩**
- [ ] **Step 2: 加入 `bleak` 依赖**
- [ ] **Step 3: 实现 Windows BLE 扫描与连接**
- [ ] **Step 4: 服务默认优先使用真实 runtime，失败时降级到 memory runtime**
- [ ] **Step 5: 更新打包脚本与文档**

## Task 7: 波形库编辑与规则编辑完善

**Files:**
- Modify: `app/bluetooth/models.py`
- Modify: `app/bluetooth/storage.py`
- Modify: `app/api/routes.py`
- Modify: `app/static/app.js`
- Modify: `app/templates/index.html`
- Test: `tests/test_bluetooth_storage.py`
- Test: `tests/test_bluetooth_api.py`

- [ ] **Step 1: 先补波形新增 / 复制 / 删除测试**
- [ ] **Step 2: 实现波形库 CRUD**
- [ ] **Step 3: 先补规则更新测试**
- [ ] **Step 4: 实现规则更新接口和前端绑定**
- [ ] **Step 5: 跑蓝牙相关回归**

## Completion Checklist

- [ ] 蓝牙配置文件可自动初始化
- [ ] 控制台可查看蓝牙状态并执行扫描 / 连接 / 断开
- [ ] 控制台已出现 EMS 波形库和规则面板
- [ ] 直播事件可触发蓝牙波形执行
- [ ] 真实 BLE runtime 已接入或已提供可验证降级路径
- [ ] 现有监听和指令通道测试无回归

## Notes

- 用户已经明确要求“继续实现”，因此本计划按 inline execution 路径直接执行，不额外等待执行方式确认。
- 当前会话不适合拉子代理做计划审稿，因此沿用本地结构化复核替代。
