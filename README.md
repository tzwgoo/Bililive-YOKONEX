# Bililive-YOKONEX

一个基于 `Python + FastAPI + Vue 3` 的本地直播互动控制台，用于接入 Bilibili 直播事件（礼物、点赞、弹幕关键词、醒目留言、舰队、互动），并映射为固定指令槽位 `command_one` ~ `command_ten`，发往下游 WebSocket 指令服务或蓝牙 EMS 设备。

## 界面预览

![Bililive-YOKONEX 控制台预览](docs/assets/github-home.png)

## 核心功能

### 直播事件监听

- **双监听模式**：官方 `open-live`（B 站开放平台）和第三方房间消息流 `LiveDanmaku`
- 两种模式共用同一套本地控制台、映射规则和下游指令通道
- 支持实时展示礼物、弹幕、点赞、醒目留言、舰队、互动事件流

### 指令分发

- **IM 模式**：礼物按价格区间、点赞按倍数阈值、弹幕按关键词 → 命中固定指令槽位 → 发往下游 WebSocket
- **蓝牙模式**：事件匹配蓝牙规则 → 触发 EMS 波形输出
- 两种礼物触发模式：`单次触发` 或 `按礼物数量触发`
- 弹幕支持冷却时间、每用户限流、舰队等级过滤

### Web 控制台

- **主控台** `/`：运行状态总览、会话控制、下游连接管理、实时事件日志
- **事件配置** `/events`：IM 规则和蓝牙事件规则的可视化编辑
- **波形库** `/waveforms`：蓝牙波形的创建、编辑、预览和分段管理
- **OBS 小窗** `/bluetooth/overlay`：A/B 通道强度、波形曲线、最近触发事件的实时展示

### 蓝牙 EMS 输出

- 蓝牙 BLE 设备扫描与连接
- 内置波形库 + 自定义波形编辑
- 事件规则绑定：按价格区间、弹幕关键词匹配后触发波形
- OBS 小窗实时状态 SSE 推送

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.11+ / FastAPI / Uvicorn |
| 前端框架 | Vue 3 + TypeScript + Vite |
| UI 组件库 | Ant Design Vue 4 |
| 状态管理 | Pinia |
| 实时通信 | WebSocket / SSE (Server-Sent Events) |
| 蓝牙 | Bleak (跨平台 BLE) |
| B 站 API | bilibili-api-python |
| 测试 | pytest / pytest-asyncio / Vitest |
| 打包 | PyInstaller (Windows EXE) |
| CI/CD | GitHub Actions |

## 项目结构

```text
app/
  api/                  HTTP API 路由
  bilibili/             官方 open-live（签名、HTTP 客户端、WS 协议）
  bluetooth/            蓝牙 EMS 子系统（BLE 运行时、调度器、波形库、存储）
  command_gateway/      下游 WebSocket 指令通道（登录、发送指令、心跳）
  services/             业务服务层（事件中心、礼物/弹幕分发、会话管理）
  static/               旧版前端脚本与样式
  templates/            页面模板（含 OBS 小窗）
  third_party/          第三方房间消息流适配（WS 客户端、事件映射）
config/
  gift_command_mappings.json   礼物映射规则
  bluetooth_settings.json      蓝牙配置（运行时生成）
frontend/               Vue 3 SPA 前端（Vite + TypeScript + Ant Design Vue）
  src/
    pages/              DashboardPage / EventConfigPage / WaveformLibraryPage
    components/         组件（dashboard / events / waveforms / layout / shared）
    stores/             Pinia 状态管理
    composables/        组合式函数（SSE 流、轮询、本地草稿）
    services/           API 调用封装
    types/              TypeScript 类型定义
tests/                  后端 + 前端测试（26 个后端 + 15 个前端）
docs/                   文档（使用说明、WS API、发布指南、设计规格）
run_app.py              应用入口
build_exe.ps1           Windows EXE 打包脚本
```

## 环境要求

- Python `3.11+`
- Windows 本地运行或打包环境
- 第三方模式下可访问普通 B 站直播间消息流
- 官方模式下额外需要：
  - B 站开放平台 `APP_ID`
  - `BILI_ACCESS_KEY_ID`
  - `BILI_ACCESS_KEY_SECRET`
  - 主播身份码 `code`

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 `.env`

参考 `.env.example` 创建 `.env`：

```env
APP_ID=1234567890123
BILI_ACCESS_KEY_ID=your_access_key_id
BILI_ACCESS_KEY_SECRET=your_access_key_secret
GIFT_MAPPING_PATH=config/gift_command_mappings.json
```

> **说明**：
> - 仅使用第三方模式可不填开放平台字段
> - 主播身份码 `code` 和下游指令通道参数在页面中手动输入

### 3. 配置礼物映射（可选）

参考 `config/gift_command_mappings.example.json`，默认配置已预置四组独立事件规则：

| 事件类型 | 说明 |
|----------|------|
| `gift` | 普通礼物 |
| `super_chat` | 醒目留言 |
| `guard_buy` | 上舰 |
| `guard_renew` | 续费 |

```json
{
  "rules": [
    { "min_price": 0, "max_price": 99, "command_slot": "command_one" },
    { "event_type": "super_chat", "min_price": 30, "max_price": 49, "command_slot": "command_one" },
    { "event_type": "guard_buy", "min_price": 100000, "max_price": 999999, "command_slot": "command_eight" }
  ],
  "like_rules": [
    { "like_multiple": 100, "command_slot": "command_three" }
  ]
}
```

### 4. 启动服务

```bash
# 方式一：直接运行（自动打开浏览器）
python run_app.py

# 方式二：使用 uvicorn（开发模式，支持热重载）
uvicorn app.main:app --reload
```

启动后访问 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

### 5. 使用流程

1. 打开主控台 `/`，选择监听模式（官方 / 第三方）
2. 选择礼物触发模式（按数量 / 单次）
3. 输入下游 WebSocket 地址并登录指令通道
4. 官方模式输入主播身份码，第三方模式输入房间长 ID
5. 点击"启动监听"
6. 在 `/events` 页面维护 IM 档位规则和蓝牙事件绑定规则
7. 在 `/waveforms` 页面管理蓝牙波形

## 指令槽位

`command_slot` 仅允许以下 10 个固定值：

`command_one` · `command_two` · `command_three` · `command_four` · `command_five` · `command_six` · `command_seven` · `command_eight` · `command_nine` · `command_ten`

下游服务接收到的 `commandId` 即为命中的 `command_slot`。

## 打包为 EXE

```powershell
.\build_exe.ps1
```

产物输出至 `dist/BiliLive-YOKONEX/`，启动文件为 `BiliLive-YOKONEX.exe`。

打包流程自动包含：Python 依赖、前端构建产物、模板文件、配置文件、文档。

## 自动发布 Release

推送版本标签后，GitHub Actions 自动构建并创建 GitHub Release：

```bash
git tag v0.1.0
git push origin v0.1.0
```

CI 流程：
- 在 `windows-latest` 上安装依赖
- 运行关键测试
- 执行 `build_exe.ps1`
- 生成 zip 包并上传至 Release

## 测试

```bash
# 全量测试
pytest -v

# 仅前端资源回归
pytest tests/test_frontend_assets.py -v
```

## 详细文档

| 文档 | 说明 |
|------|------|
| [使用说明](docs/使用说明.md) | 完整中文使用指南（配置、启动、蓝牙小窗、排查） |
| [WebSocket API](docs/WEBSOCKET_API.md) | 下游 WebSocket 协议文档（多语言示例） |
| [发布指南](docs/release-guide.md) | Release 自动/手动发布流程 |

## 常见问题

### 官方模式提示配置缺失

请检查 `.env` 是否存在，并确认 `APP_ID`、`BILI_ACCESS_KEY_ID`、`BILI_ACCESS_KEY_SECRET` 已填写。仅使用第三方模式可忽略此提示。

### `7007` 身份码错误

主播身份码 `code` 无效或已过期，请重新获取。

### `7003` 心跳过期

当前 `game_id` 已失效，需要重新启动监听。

### `7010` 超过连接上限

同一直播间下同一应用连接数超限，请先停止旧连接。

## License

本项目仅供学习交流使用。
