# EMS 蓝牙电量与自动重连实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 EMS 蓝牙连接补充默认自动重连，并把设备电量接入状态接口与 OBS 小窗显示。

**Architecture:** 参考 `D:\STS2-Link-YOKONEX` 的 EMS 协议处理方式，在 bleak 运行时中增加通知订阅、`0x35 0x71 0x04` 电量查询包与响应解析。服务层负责把运行时中的电量值规范化并透传给 `/api/bluetooth/status` 与 `/api/bluetooth/overlay/status`，前端 overlay 仅消费新增字段并显示。

**Tech Stack:** Python, FastAPI, bleak, pytest, 原生 HTML/CSS/JavaScript

---

### Task 1: 先补电量与自动重连的失败测试

**Files:**
- Modify: `tests/test_bleak_runtime.py`
- Modify: `tests/test_bluetooth_service.py`
- Modify: `tests/test_bluetooth_api.py`
- Modify: `tests/test_frontend_assets.py`

- [ ] 为 bleak 运行时增加“连接后发送 EMS 电量查询包”和“收到通知后解析电量”的失败测试。
- [ ] 为蓝牙服务增加状态接口和 overlay payload 都带 `battery_level` 的失败测试。
- [ ] 为 API 层和前端模板增加电量字段展示断言。
- [ ] 运行定向测试，确认它们先失败。

### Task 2: 实现运行时电量读取与默认自动重连

**Files:**
- Modify: `app/bluetooth/models.py`
- Modify: `app/bluetooth/runtime/base.py`
- Modify: `app/bluetooth/runtime/bleak_runtime.py`
- Modify: `app/bluetooth/runtime/memory_runtime.py`
- Modify: `config/bluetooth_settings.json`

- [ ] 把蓝牙配置默认 `auto_reconnect` 改为 `True`，并同步当前本地配置文件。
- [ ] 给运行时状态和 overlay payload 增加 `battery_level`。
- [ ] 在 bleak 运行时中接入通知特征订阅、电量查询包发送和通知解析。
- [ ] 确保断开或重连后电量状态同步重置或刷新。

### Task 3: 透传到 API 与 OBS 小窗

**Files:**
- Modify: `app/bluetooth/service.py`
- Modify: `app/templates/bluetooth_overlay.html`
- Modify: `app/static/bluetooth_overlay.js`

- [ ] 服务层把运行时电量透传到状态 payload 与 overlay payload。
- [ ] OBS 小窗增加电量显示区域，并处理未知电量展示。
- [ ] 保持现有布局风格不被破坏。

### Task 4: 验证

**Files:**
- Test: `tests/test_bleak_runtime.py`
- Test: `tests/test_bluetooth_service.py`
- Test: `tests/test_bluetooth_api.py`
- Test: `tests/test_frontend_assets.py`

- [ ] 运行定向 pytest，确认新旧相关测试通过。
- [ ] 检查工作区 diff，确认没有误改无关文件。
