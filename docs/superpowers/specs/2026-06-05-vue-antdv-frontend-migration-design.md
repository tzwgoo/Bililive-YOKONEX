# Vue + Ant Design Vue 前端迁移设计文档

## 1. 背景

当前项目前端由 `FastAPI + Jinja2 模板 + 原生 JavaScript/CSS` 组成，已具备完整业务能力，但随着控制台、蓝牙规则页、IM 规则页的复杂度增长，前端代码出现以下问题：

- 模板、样式、交互逻辑耦合较高，页面演进成本上升。
- 多页面共享状态、轮询逻辑、事件流渲染逻辑难以复用。
- 组件边界不清晰，不利于后续继续扩展复杂交互。
- 当前没有独立前端工程，开发体验、类型约束、组件复用能力都受限。

本次改造目标是将现有三页前端重构为 `Vue 3 + Vite + TypeScript + Ant Design Vue` 的独立 SPA，同时保持现有功能和 FastAPI API 兼容。

## 2. 目标与范围

### 2.1 目标

- 将主控台、蓝牙规则页、IM 规则页迁移为单页应用。
- 保持现有功能和交互语义尽量 1:1，不主动调整业务规则。
- 引入独立前端工程与构建链路，开发时前后端分开运行。
- 生产时由 FastAPI 托管前端构建产物。
- 为未来彻底独立部署前端保留清晰边界。

### 2.2 非目标

- 本阶段不主动重构后端 API 协议。
- 本阶段不改变事件流来源、轮询机制、SSE 机制。
- 本阶段不引入新的业务能力或重新设计信息架构。
- 本阶段不要求把蓝牙、IM、直播链路改造成新的后端分层。

## 3. 总体方案

采用“前端工程独立、生产托管仍由 FastAPI 提供”的折中方案：

- 新建 `frontend/` 目录，使用 `Vue 3 + Vite + TypeScript + Ant Design Vue`。
- 开发期：
  - Vite dev server 负责前端页面与热更新。
  - FastAPI 继续提供现有 API 与 SSE。
  - Vite 代理 `/api` 到 FastAPI。
- 生产期：
  - Vite 构建产物输出到固定目录。
  - FastAPI 挂载静态目录并对前端路由做 SPA fallback。

这样做的好处：

- 现在迁移成本可控。
- 现有 Python 后端启动和发布方式仍可复用。
- 未来如果要改成完全独立部署，只需调整部署链路，不需要重写前端结构。

## 4. 技术选型

- 前端框架：`Vue 3`
- 构建工具：`Vite`
- 语言：`TypeScript`
- UI 组件库：`Ant Design Vue`
- 路由：`Vue Router`
- 状态管理：`Pinia`
- HTTP：优先使用原生 `fetch` 封装，减少额外依赖
- 实时流：保留 `EventSource`，封装为 composable

说明：

- 选择 `TypeScript` 是为了给复杂页面状态、SSE 事件、后端返回结构提供明确边界。
- 选择 `Pinia` 而不是自定义全局对象，是因为后续跨页面共享连接状态和运行状态会更稳定。
- 选择 `Ant Design Vue` 作为 UI 基础层，但不会强行让所有复杂业务 UI 都变成“纯组件库默认样式”，必要时保留项目自定义风格。

## 5. 页面结构

前端为单页应用，统一使用前端路由：

- `/`：主控台 `DashboardPage`
- `/bluetooth/studio`：蓝牙规则页 `BluetoothStudioPage`
- `/command/studio`：IM 规则页 `CommandStudioPage`

### 5.1 主控台页面拆分

`DashboardPage` 建议拆分为：

- `DashboardLayout`
- `SessionConfigCard`
- `TriggerConfigCard`
- `ConnectionPanel`
- `RuntimeSnapshotCard`
- `EventStreamTabs`
- `EventList`
- `StatusPill`

### 5.2 蓝牙规则页拆分

`BluetoothStudioPage` 建议拆分为：

- `WaveformLibraryPanel`
- `WaveformEditorPanel`
- `WaveformCanvas`
- `WaveformStepsTable`
- `BluetoothRuleGroupsPanel`

### 5.3 IM 规则页拆分

`CommandStudioPage` 建议拆分为：

- `GiftRuleGroupsPanel`
- `FixedLikeCommandPanel`
- `FixedDanmakuCommandPanel`

## 6. 前端目录设计

建议目录结构如下：

```text
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  src/
    main.ts
    App.vue
    router/
      index.ts
    layouts/
      AppShell.vue
    pages/
      DashboardPage.vue
      BluetoothStudioPage.vue
      CommandStudioPage.vue
    components/
      dashboard/
      bluetooth/
      command/
      shared/
    stores/
      session.ts
      command.ts
      bluetooth.ts
    services/
      http.ts
      session.ts
      command.ts
      bluetooth.ts
    composables/
      useEventStream.ts
      usePolling.ts
      useLocalDraft.ts
    types/
      session.ts
      command.ts
      bluetooth.ts
      event.ts
    utils/
      format.ts
      adapters.ts
```

目录原则：

- `pages/` 只负责编排页面，不承载复杂细节。
- `components/` 按业务域拆分。
- `stores/` 只放跨组件共享的可观察状态。
- `services/` 只负责 API 请求。
- `composables/` 放轮询、SSE、本地草稿等复用逻辑。
- `types/` 保存与后端接口和页面模型相关的类型定义。

## 7. 数据流设计

前端数据分为三类：

### 7.1 HTTP 状态拉取

保留现有状态拉取接口，例如：

- `/api/status`
- `/api/command/status`
- `/api/bluetooth/status`
- `/api/bluetooth/studio`
- `/api/command/studio`

这些请求统一通过 `services/*.ts` 封装，组件不直接写裸 `fetch`。

### 7.2 用户动作提交

例如：

- 启动 / 停止监听
- 登录 / 退出 IM
- 扫描 / 连接 / 断开蓝牙
- 保存蓝牙规则
- 保存 IM 规则

这些动作由页面调用 service，再由 store 或局部状态消费结果。

### 7.3 实时事件流

保留现有 `EventSource` 方案：

- `/api/events/stream`
- `/api/control/stream`

统一封装为 `useEventStream()`，负责：

- 建立连接
- 自动更新响应式数据
- 错误提示与重连策略
- 页面卸载时清理连接

## 8. 状态管理设计

至少拆成三个 store：

- `sessionStore`
  - 监听状态
  - 当前模式
  - 草稿参数
  - 最近事件时间
- `commandStore`
  - IM 登录状态
  - 当前 UID / userId
  - 最近登录时间
  - IM 规则页数据
- `bluetoothStore`
  - 蓝牙连接状态
  - 设备列表
  - 波形库
  - 规则页数据

状态设计原则：

- 跨页面共享的状态进入 store。
- 仅当前组件使用的编辑态、弹窗态保留在组件局部。
- 本地缓存（如草稿）通过 composable 与 `localStorage` 管理，而不是散落到页面内。

## 9. 与 FastAPI 的集成

### 9.1 开发期

- 前端运行：`vite`
- 后端运行：`uvicorn`
- 通过 Vite 代理 `/api` 到 FastAPI

预期体验：

- 前端热更新独立生效
- 后端接口不需要因为样式改动重启

### 9.2 生产期

- `vite build` 输出到固定目录，例如 `frontend/dist`
- FastAPI 挂载该目录的静态资源
- 对非 `/api` 路径统一回退到 `index.html`

### 9.3 启动方式

建议后续支持：

- 开发启动：前后端两个命令
- 生产启动：仍由 Python 服务提供页面

## 10. 渐进迁移策略

### 阶段 1：搭前端工程骨架

- 初始化 `frontend/`
- 接入 Vue、TS、Vite、Ant Design Vue、Vue Router、Pinia
- 配置开发代理
- 建立基础 `AppShell`

### 阶段 2：迁主控台

- 先完成主控台页面
- 打通状态拉取、启动/停止、连接切换、事件流
- 用 Vue 组件替代当前模板结构

### 阶段 3：迁蓝牙规则页

- 迁波形库、波形编辑、规则保存
- 保留现有接口和行为

### 阶段 4：迁 IM 规则页

- 迁价格档位编辑
- 迁固定点赞 / 弹幕指令展示

### 阶段 5：切换入口

- FastAPI 页面入口改为指向 SPA
- 保留 API 路由
- 清理旧模板和原生前端资源

## 11. 风险与应对

### 风险 1：SSE 与轮询逻辑迁移后行为不一致

应对：

- 在 `useEventStream` 和 `usePolling` 中复刻现有逻辑
- 迁移时优先保持行为一致，再讨论优化

### 风险 2：现有接口字段不够适合前端直接消费

应对：

- 先在前端 `adapters.ts` 中做转换
- 第一阶段不强行改后端协议

### 风险 3：波形编辑器从原生 DOM 迁到 Vue 时复杂度上升

应对：

- 将编辑器拆成独立业务组件
- 保留现有交互模型，不同时重写交互哲学

### 风险 4：发布链路受前端构建影响

应对：

- 在发布前补充前端构建步骤
- 明确开发与生产构建命令

## 12. 验收标准

### 功能验收

- 主控台三大区块都可正常使用
- IM 连接与蓝牙连接均可工作
- 事件流、控制日志流可正常渲染
- 蓝牙规则页可加载、编辑、保存
- IM 规则页可加载、编辑、保存

### 技术验收

- 前端具备独立构建与开发环境
- 生产环境可由 FastAPI 托管前端产物
- 前端页面基于 Vue Router 路由切换
- API 调用与 SSE 逻辑已封装，不散落在页面组件内
- 原生模板和脚本可以平滑下线

### 迁移边界验收

- 不要求本阶段优化业务协议
- 不要求本阶段重构后端服务结构
- 不要求本阶段新增业务功能

## 13. 推荐实施策略

推荐采用“1:1 功能迁移 + 轻度前端结构治理”的策略：

- 功能上优先保真
- 代码上优先建立 Vue 工程边界
- API 上优先兼容
- 部署上优先稳态演进

这样既能尽快完成技术栈切换，又不会把问题扩散成前后端同时重写的大改造。
