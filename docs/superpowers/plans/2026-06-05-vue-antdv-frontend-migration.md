# Vue + Ant Design Vue 前端迁移 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有主控台、蓝牙规则页、IM 规则页从 `FastAPI + Jinja2 + 原生 JavaScript/CSS` 迁移到 `Vue 3 + Vite + TypeScript + Ant Design Vue` 单页应用，同时保持现有功能与 FastAPI API 兼容。

**Architecture:** 新建独立 `frontend/` 工程，开发时由 Vite 提供页面并通过代理访问 FastAPI API，生产时由 FastAPI 托管前端构建产物并处理 SPA fallback。前端使用 `Vue Router + Pinia + composables + services` 分离页面、共享状态、SSE 和轮询逻辑；后端优先保持 API 协议兼容，只在静态托管与前端入口上做必要改造。

**Tech Stack:** Python 3.11+、FastAPI、Vue 3、Vite、TypeScript、Ant Design Vue、Vue Router、Pinia、Vitest、pytest

---

## 文件结构与职责

**前端工程骨架**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/layouts/AppShell.vue`

**前端基础设施**
- Create: `frontend/src/stores/session.ts`
- Create: `frontend/src/stores/command.ts`
- Create: `frontend/src/stores/bluetooth.ts`
- Create: `frontend/src/services/http.ts`
- Create: `frontend/src/services/session.ts`
- Create: `frontend/src/services/command.ts`
- Create: `frontend/src/services/bluetooth.ts`
- Create: `frontend/src/composables/useEventStream.ts`
- Create: `frontend/src/composables/usePolling.ts`
- Create: `frontend/src/composables/useLocalDraft.ts`
- Create: `frontend/src/types/session.ts`
- Create: `frontend/src/types/command.ts`
- Create: `frontend/src/types/bluetooth.ts`
- Create: `frontend/src/types/event.ts`
- Create: `frontend/src/utils/format.ts`
- Create: `frontend/src/utils/adapters.ts`

**页面与组件**
- Create: `frontend/src/pages/DashboardPage.vue`
- Create: `frontend/src/pages/BluetoothStudioPage.vue`
- Create: `frontend/src/pages/CommandStudioPage.vue`
- Create: `frontend/src/components/shared/StatusPill.vue`
- Create: `frontend/src/components/shared/EventList.vue`
- Create: `frontend/src/components/shared/EventStreamTabs.vue`
- Create: `frontend/src/components/dashboard/SessionConfigCard.vue`
- Create: `frontend/src/components/dashboard/TriggerConfigCard.vue`
- Create: `frontend/src/components/dashboard/ConnectionPanel.vue`
- Create: `frontend/src/components/dashboard/RuntimeSnapshotCard.vue`
- Create: `frontend/src/components/bluetooth/WaveformLibraryPanel.vue`
- Create: `frontend/src/components/bluetooth/WaveformEditorPanel.vue`
- Create: `frontend/src/components/bluetooth/WaveformCanvas.vue`
- Create: `frontend/src/components/bluetooth/WaveformStepsTable.vue`
- Create: `frontend/src/components/bluetooth/BluetoothRuleGroupsPanel.vue`
- Create: `frontend/src/components/command/GiftRuleGroupsPanel.vue`
- Create: `frontend/src/components/command/FixedLikeCommandPanel.vue`
- Create: `frontend/src/components/command/FixedDanmakuCommandPanel.vue`

**前端样式与资源**
- Create: `frontend/src/styles/reset.css`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/app.css`

**前端测试**
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/tests/setup.ts`
- Create: `frontend/src/tests/router.spec.ts`
- Create: `frontend/src/tests/services.adapters.spec.ts`
- Create: `frontend/src/tests/composables.event-stream.spec.ts`
- Create: `frontend/src/tests/pages.dashboard.spec.ts`
- Create: `frontend/src/tests/pages.bluetooth-studio.spec.ts`
- Create: `frontend/src/tests/pages.command-studio.spec.ts`

**后端集成**
- Modify: `app/main.py`
- Modify: `app/api/routes.py`
- Modify: `app/runtime.py`
- Possibly Modify: `build_exe.ps1`

**旧前端入口清理**
- Modify: `app/templates/index.html`
- Modify: `app/templates/bluetooth_studio.html`
- Modify: `app/templates/command_studio.html`
- Modify: `app/static/app.js`
- Modify: `app/static/bluetooth_studio.js`
- Modify: `app/static/command_studio.js`
- Modify: `app/static/style.css`

**后端测试与文档**
- Modify: `tests/test_frontend_assets.py`
- Modify: `tests/test_api_routes.py`
- Modify: `tests/test_build_script.py`
- Modify: `README.md`
- Modify: `docs/使用说明.md`

**参考文档**
- Spec: `docs/superpowers/specs/2026-06-05-vue-antdv-frontend-migration-design.md`

## 实施原则

1. 先搭建前端工程和测试骨架，再迁页面。
2. 每个功能块遵守 TDD：先写失败测试，再做最小实现。
3. 第一轮优先 1:1 功能迁移，不主动优化业务协议。
4. 所有 API 调用统一进 `services/`，所有 SSE / 轮询逻辑统一进 `composables/`。
5. 生产入口切换前，保证 FastAPI API 与前端构建链路均可独立验证。

### Task 1: 建立前端工程骨架与基础构建链路

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/layouts/AppShell.vue`
- Create: `frontend/src/styles/reset.css`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/app.css`

- [ ] **Step 1: 为前端工程存在性写后端前端资产失败测试**

```python
def test_frontend_workspace_contains_vite_entrypoints() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    assert (base_dir / "frontend" / "package.json").exists()
    assert (base_dir / "frontend" / "vite.config.ts").exists()
    assert (base_dir / "frontend" / "src" / "main.ts").exists()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_frontend_assets.py -k vite_entrypoints -v`
Expected: FAIL，提示 `frontend/package.json` 或 `frontend/src/main.ts` 不存在

- [ ] **Step 3: 创建 `frontend/package.json` 与最小脚本**

```json
{
  "name": "bililive-yokonex-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run"
  }
}
```

- [ ] **Step 4: 创建 `vite.config.ts`、`main.ts`、`App.vue` 和基础样式入口**

```ts
import { createApp } from "vue";
import App from "./App.vue";
createApp(App).mount("#app");
```

- [ ] **Step 5: 创建 `Vue Router` 与 `AppShell` 最小骨架**

```ts
createRouter({
  history: createWebHistory(),
  routes: [],
});
```

- [ ] **Step 6: 再次运行测试确认通过**

Run: `pytest tests/test_frontend_assets.py -k vite_entrypoints -v`
Expected: PASS

- [ ] **Step 7: 运行前端构建确认骨架可编译**

Run: `cd frontend && npm install && npm run build`
Expected: PASS，输出 `dist/` 产物

- [ ] **Step 8: Commit**

```bash
git add frontend tests/test_frontend_assets.py
git commit -m "feat(frontend): 初始化 Vue 与 Vite 前端工程骨架"
```

### Task 2: 建立 Pinia、services、composables 与类型层基础设施

**Files:**
- Create: `frontend/src/stores/session.ts`
- Create: `frontend/src/stores/command.ts`
- Create: `frontend/src/stores/bluetooth.ts`
- Create: `frontend/src/services/http.ts`
- Create: `frontend/src/services/session.ts`
- Create: `frontend/src/services/command.ts`
- Create: `frontend/src/services/bluetooth.ts`
- Create: `frontend/src/composables/useEventStream.ts`
- Create: `frontend/src/composables/usePolling.ts`
- Create: `frontend/src/composables/useLocalDraft.ts`
- Create: `frontend/src/types/session.ts`
- Create: `frontend/src/types/command.ts`
- Create: `frontend/src/types/bluetooth.ts`
- Create: `frontend/src/types/event.ts`
- Create: `frontend/src/utils/format.ts`
- Create: `frontend/src/utils/adapters.ts`
- Create: `frontend/src/tests/services.adapters.spec.ts`
- Create: `frontend/src/tests/composables.event-stream.spec.ts`

- [ ] **Step 1: 为状态适配层写失败测试**

```ts
it("maps backend session status into dashboard model", () => {
  const result = adaptSessionStatus({ status: "running", room_id: 123 });
  expect(result.roomId).toBe("123");
});
```

- [ ] **Step 2: 为 `useEventStream` 写失败测试**

```ts
it("pushes incoming SSE events into reactive list", async () => {
  const { events } = useEventStream("/api/events/stream");
  expect(events.value).toHaveLength(1);
});
```

- [ ] **Step 3: 运行 Vitest 确认失败**

Run: `cd frontend && npm run test -- services.adapters composables.event-stream`
Expected: FAIL，提示适配器或 composable 未实现

- [ ] **Step 4: 实现统一 `http.ts` 与最小 service 封装**

```ts
export async function requestJson<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  return await response.json() as T;
}
```

- [ ] **Step 5: 实现类型定义与 `adapters.ts`**

```ts
export function adaptSessionStatus(payload: SessionStatusResponse): SessionStatusModel {
  return { roomId: String(payload.room_id || "-") };
}
```

- [ ] **Step 6: 实现 `useEventStream`、`usePolling`、`useLocalDraft` 最小可运行版本**

```ts
const source = new EventSource(url);
source.onmessage = (event) => events.value.unshift(JSON.parse(event.data));
```

- [ ] **Step 7: 再次运行 Vitest 确认通过**

Run: `cd frontend && npm run test -- services.adapters composables.event-stream`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add frontend/src/services frontend/src/stores frontend/src/composables frontend/src/types frontend/src/utils frontend/src/tests
git commit -m "feat(frontend): 建立 API 服务层、状态层与事件流基础设施"
```

### Task 3: 迁移主控台路由、布局与只读状态渲染

**Files:**
- Create: `frontend/src/pages/DashboardPage.vue`
- Create: `frontend/src/components/shared/StatusPill.vue`
- Create: `frontend/src/components/shared/EventList.vue`
- Create: `frontend/src/components/shared/EventStreamTabs.vue`
- Create: `frontend/src/components/dashboard/RuntimeSnapshotCard.vue`
- Modify: `frontend/src/router/index.ts`
- Create: `frontend/src/tests/router.spec.ts`
- Create: `frontend/src/tests/pages.dashboard.spec.ts`

- [ ] **Step 1: 为主控台路由与空页面渲染写失败测试**

```ts
it("renders dashboard route at slash", async () => {
  router.push("/");
  await router.isReady();
  expect(screen.getByText("直播互动监听控制台")).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm run test -- router pages.dashboard`
Expected: FAIL，提示页面组件不存在或路由未配置

- [ ] **Step 3: 实现 `DashboardPage` 与 `AppShell` 基础布局**

```vue
<template>
  <AppShell>
    <DashboardPage />
  </AppShell>
</template>
```

- [ ] **Step 4: 接入 `StatusPill`、`RuntimeSnapshotCard` 与事件流标签容器**

```vue
<EventStreamTabs :tabs="tabs" />
```

- [ ] **Step 5: 使用 `sessionStore` / `commandStore` / `bluetoothStore` 拉取只读状态**

```ts
onMounted(() => sessionStore.startPolling());
```

- [ ] **Step 6: 再次运行测试确认通过**

Run: `cd frontend && npm run test -- router pages.dashboard`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages frontend/src/components/shared frontend/src/components/dashboard frontend/src/router frontend/src/tests
git commit -m "feat(frontend): 迁移主控台基础布局与只读状态展示"
```

### Task 4: 迁移主控台交互表单、连接中心与实时事件流

**Files:**
- Create: `frontend/src/components/dashboard/SessionConfigCard.vue`
- Create: `frontend/src/components/dashboard/TriggerConfigCard.vue`
- Create: `frontend/src/components/dashboard/ConnectionPanel.vue`
- Modify: `frontend/src/pages/DashboardPage.vue`
- Modify: `frontend/src/stores/session.ts`
- Modify: `frontend/src/stores/command.ts`
- Modify: `frontend/src/stores/bluetooth.ts`
- Modify: `frontend/src/tests/pages.dashboard.spec.ts`

- [ ] **Step 1: 为启动监听表单写失败测试**

```ts
it("submits session start payload from dashboard form", async () => {
  await user.click(screen.getByRole("button", { name: "启动监听" }));
  expect(mockStartSession).toHaveBeenCalled();
});
```

- [ ] **Step 2: 为 IM / 蓝牙连接切换写失败测试**

```ts
it("switches between im and bluetooth panels", async () => {
  await user.selectOptions(screen.getByLabelText("连接方式"), "bluetooth");
  expect(screen.getByText("蓝牙连接")).toBeInTheDocument();
});
```

- [ ] **Step 3: 为事件流列表渲染写失败测试**

```ts
it("renders interact and control events in tabs", async () => {
  expect(screen.getByText("互动事件")).toBeInTheDocument();
  expect(screen.getByText("控制日志")).toBeInTheDocument();
});
```

- [ ] **Step 4: 运行测试确认失败**

Run: `cd frontend && npm run test -- pages.dashboard`
Expected: FAIL，提示表单提交、连接面板切换或事件流渲染未实现

- [ ] **Step 5: 实现 `SessionConfigCard` 与 `TriggerConfigCard`**

```vue
<a-form @finish="handleSubmit">
  <a-select v-model:value="draft.mode" />
</a-form>
```

- [ ] **Step 6: 实现 `ConnectionPanel` 与 IM / 蓝牙切换逻辑**

```vue
<a-segmented v-model:value="connectionMode" :options="options" />
```

- [ ] **Step 7: 接入 `useLocalDraft`、`usePolling` 与 `useEventStream` 到主控台**

```ts
const { events: liveEvents } = useEventStream("/api/events/stream");
const { events: controlEvents } = useEventStream("/api/control/stream");
```

- [ ] **Step 8: 再次运行测试确认通过**

Run: `cd frontend && npm run test -- pages.dashboard`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/dashboard frontend/src/pages/DashboardPage.vue frontend/src/stores frontend/src/tests/pages.dashboard.spec.ts
git commit -m "feat(frontend): 迁移主控台交互表单与实时事件流"
```

### Task 5: 迁移蓝牙规则页与波形编辑器

**Files:**
- Create: `frontend/src/pages/BluetoothStudioPage.vue`
- Create: `frontend/src/components/bluetooth/WaveformLibraryPanel.vue`
- Create: `frontend/src/components/bluetooth/WaveformEditorPanel.vue`
- Create: `frontend/src/components/bluetooth/WaveformCanvas.vue`
- Create: `frontend/src/components/bluetooth/WaveformStepsTable.vue`
- Create: `frontend/src/components/bluetooth/BluetoothRuleGroupsPanel.vue`
- Modify: `frontend/src/stores/bluetooth.ts`
- Create: `frontend/src/tests/pages.bluetooth-studio.spec.ts`

- [ ] **Step 1: 为蓝牙规则页初始加载写失败测试**

```ts
it("loads waveform library and rule groups", async () => {
  expect(await screen.findByText("波形库")).toBeInTheDocument();
  expect(await screen.findByText("事件规则")).toBeInTheDocument();
});
```

- [ ] **Step 2: 为波形编辑动作写失败测试**

```ts
it("updates waveform draft name and save action", async () => {
  await user.type(screen.getByPlaceholderText("输入波形名称"), "测试波形");
  expect(mockUpdateWaveform).toHaveBeenCalled();
});
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd frontend && npm run test -- pages.bluetooth-studio`
Expected: FAIL，提示页面、波形库或规则组件未实现

- [ ] **Step 4: 实现 `BluetoothStudioPage` 与数据装载**

```ts
onMounted(() => bluetoothStore.fetchStudio());
```

- [ ] **Step 5: 实现波形库、波形编辑器、规则分组组件**

```vue
<WaveformLibraryPanel :waveforms="store.waveforms" />
<WaveformEditorPanel :draft="store.draftWaveform" />
<BluetoothRuleGroupsPanel :groups="store.ruleGroups" />
```

- [ ] **Step 6: 将当前原生拖拽/分段编辑逻辑迁入 `bluetoothStore` 或局部 composable**

```ts
function updateDraftStep(index: number, patch: Partial<WaveformStepModel>) {
  store.updateDraftStep(index, patch);
}
```

- [ ] **Step 7: 再次运行测试确认通过**

Run: `cd frontend && npm run test -- pages.bluetooth-studio`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/BluetoothStudioPage.vue frontend/src/components/bluetooth frontend/src/stores/bluetooth.ts frontend/src/tests/pages.bluetooth-studio.spec.ts
git commit -m "feat(frontend): 迁移蓝牙规则页与波形编辑器"
```

### Task 6: 迁移 IM 规则页

**Files:**
- Create: `frontend/src/pages/CommandStudioPage.vue`
- Create: `frontend/src/components/command/GiftRuleGroupsPanel.vue`
- Create: `frontend/src/components/command/FixedLikeCommandPanel.vue`
- Create: `frontend/src/components/command/FixedDanmakuCommandPanel.vue`
- Modify: `frontend/src/stores/command.ts`
- Create: `frontend/src/tests/pages.command-studio.spec.ts`

- [ ] **Step 1: 为 IM 规则页加载写失败测试**

```ts
it("renders gift rule groups and fixed command panels", async () => {
  expect(await screen.findByText("礼物与独立事件价格档位")).toBeInTheDocument();
  expect(await screen.findByText("固定点赞指令 ID")).toBeInTheDocument();
});
```

- [ ] **Step 2: 为价格档位编辑与保存写失败测试**

```ts
it("submits updated command rules", async () => {
  await user.click(screen.getByRole("button", { name: "保存 IM 规则" }));
  expect(mockSaveCommandRules).toHaveBeenCalled();
});
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd frontend && npm run test -- pages.command-studio`
Expected: FAIL，提示页面或规则组件未实现

- [ ] **Step 4: 实现 `CommandStudioPage` 与 `commandStore.fetchStudio()`**

```ts
onMounted(() => commandStore.fetchStudio());
```

- [ ] **Step 5: 实现价格规则、固定点赞、固定弹幕组件**

```vue
<GiftRuleGroupsPanel :groups="store.groupedRules" />
<FixedLikeCommandPanel :command-id="store.likeCommandId" />
```

- [ ] **Step 6: 接入价格排序、新增档位、删除档位与保存动作**

```ts
store.sortGiftRules(eventType);
await store.saveRules();
```

- [ ] **Step 7: 再次运行测试确认通过**

Run: `cd frontend && npm run test -- pages.command-studio`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/CommandStudioPage.vue frontend/src/components/command frontend/src/stores/command.ts frontend/src/tests/pages.command-studio.spec.ts
git commit -m "feat(frontend): 迁移 IM 规则页"
```

### Task 7: 让 FastAPI 托管前端构建产物并切换页面入口

**Files:**
- Modify: `app/main.py`
- Modify: `app/api/routes.py`
- Modify: `app/runtime.py`
- Modify: `tests/test_api_routes.py`
- Modify: `tests/test_frontend_assets.py`

- [ ] **Step 1: 为 SPA 静态托管与路由 fallback 写失败测试**

```python
def test_frontend_spa_routes_fall_back_to_index_html(client) -> None:
    response = client.get("/bluetooth/studio")
    assert response.status_code == 200
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_api_routes.py tests/test_frontend_assets.py -k spa -v`
Expected: FAIL，提示路由仍由旧模板处理或未托管前端产物

- [ ] **Step 3: 在 `app/main.py` 中挂载前端构建目录与 fallback**

```python
app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
```

- [ ] **Step 4: 保留 `/api` 路由优先级，确保 API 不被前端静态托管覆盖**

```python
app.include_router(router, prefix="/api")
```

- [ ] **Step 5: 调整旧模板入口测试为“前端工程存在 + FastAPI 托管 SPA”**

```python
assert 'frontend/dist' in app_main_source
```

- [ ] **Step 6: 再次运行测试确认通过**

Run: `pytest tests/test_api_routes.py tests/test_frontend_assets.py -k spa -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/main.py app/api/routes.py app/runtime.py tests/test_api_routes.py tests/test_frontend_assets.py
git commit -m "feat(frontend): 接入 FastAPI 托管 Vue 构建产物"
```

### Task 8: 更新打包、文档与最终验证

**Files:**
- Modify: `build_exe.ps1`
- Modify: `README.md`
- Modify: `docs/使用说明.md`
- Modify: `tests/test_build_script.py`

- [ ] **Step 1: 为构建脚本增加前端构建步骤写失败测试**

```python
def test_build_script_runs_frontend_build() -> None:
    assert "npm run build" in script
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_build_script.py -v`
Expected: FAIL，提示构建脚本尚未包含前端构建步骤

- [ ] **Step 3: 在 `build_exe.ps1` 中加入前端依赖安装与构建**

```powershell
Push-Location frontend
npm install
npm run build
Pop-Location
```

- [ ] **Step 4: 更新 README 与使用说明的启动方式**

```markdown
- 前端开发：`cd frontend && npm run dev`
- 后端开发：`uvicorn app.main:app --reload`
```

- [ ] **Step 5: 运行文档与构建相关测试确认通过**

Run: `pytest tests/test_build_script.py tests/test_runtime.py -v`
Expected: PASS

- [ ] **Step 6: 做最终端到端验证**

Run:

```bash
cd frontend && npm run build
cd ..
pytest tests/test_api_routes.py tests/test_frontend_assets.py tests/test_third_party_mapper.py tests/test_third_party_ws_client.py -v
```

Expected: 全部 PASS，且前端构建成功

- [ ] **Step 7: Commit**

```bash
git add build_exe.ps1 README.md docs/使用说明.md tests/test_build_script.py
git commit -m "docs(frontend): 更新 Vue 前端开发与打包说明"
```
