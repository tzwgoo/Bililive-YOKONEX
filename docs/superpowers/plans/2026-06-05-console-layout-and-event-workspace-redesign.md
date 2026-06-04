# 控制台布局与事件工作区重组 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前 Vue SPA 重组为统一后台布局，并把顶层导航收敛为主控台、事件配置、波形库三个任务导向页面。

**Architecture:** 以前端信息架构重组为主，不主动重写后端规则协议。通过改造 `AppShell`、重组路由、拆分页面职责、复用现有 `stores/services` 实现页面迁移；旧路由通过前后端双层兼容重定向到新页面。

**Tech Stack:** Vue 3、Vite、TypeScript、Vue Router、Pinia、Ant Design Vue、Vitest、FastAPI、Pytest

---

## 文件结构与职责

### 需要修改的现有文件

- `frontend/src/layouts/AppShell.vue`
  - 改为左侧菜单 + 顶部标题栏 + 右侧内容区的后台壳
- `frontend/src/router/index.ts`
  - 定义新路由 `/`、`/events`、`/waveforms`，并保留旧路由重定向
- `frontend/src/styles/app.css`
  - 提供新的后台壳、侧边菜单、标题栏、内容容器通用样式
- `frontend/src/pages/DashboardPage.vue`
  - 从“全功能主页面”改造为“概览 + 高频监听控制 + 连接设备 + 日志”
- `frontend/src/pages/BluetoothStudioPage.vue`
  - 拆分出波形资产相关视图逻辑，最终作为波形库页面的来源之一
- `frontend/src/pages/CommandStudioPage.vue`
  - 拆分出 IM 规则相关视图逻辑，最终作为事件配置页面的来源之一
- `frontend/src/tests/router.spec.ts`
  - 适配新路由与旧路由重定向断言
- `frontend/src/tests/pages.dashboard.spec.ts`
  - 适配新主控台职责与结构
- `tests/test_api_routes.py`
  - 覆盖 FastAPI 对新路由 `/events`、`/waveforms` 的 SPA 托管支持
- `app/api/routes.py`
  - 增加新 SPA 路由入口，并保留旧路由的 SPA fallback

### 需要新增的文件

- `frontend/src/pages/EventConfigPage.vue`
  - 新的“事件配置”页面，容纳 `IM / 蓝牙` 双 Tag
- `frontend/src/pages/WaveformLibraryPage.vue`
  - 新的“波形库”页面，负责波形列表、预览、编辑
- `frontend/src/components/layout/AppSidebarMenu.vue`
  - 左侧一级菜单
- `frontend/src/components/layout/PageHeaderBar.vue`
  - 页面标题栏
- `frontend/src/components/dashboard/StatusSummaryGrid.vue`
  - 主控台顶部状态总览
- `frontend/src/components/dashboard/SessionControlPanel.vue`
  - 主控台监听参数与启动控制区
- `frontend/src/components/dashboard/ConnectionAndDevicesPanel.vue`
  - 主控台 IM 与蓝牙连接区
- `frontend/src/components/events/EventConfigTabs.vue`
  - 事件配置页 Tag 容器
- `frontend/src/components/events/ImRuleGroupsPanel.vue`
  - 事件配置页 IM 规则面板
- `frontend/src/components/events/BluetoothEventRulePanel.vue`
  - 事件配置页蓝牙规则面板
- `frontend/src/components/waveforms/WaveformListPanel.vue`
  - 波形库左侧列表
- `frontend/src/components/waveforms/WaveformEditorPanel.vue`
  - 波形库右侧编辑器
- `frontend/src/tests/pages.event-config.spec.ts`
  - 事件配置页行为测试
- `frontend/src/tests/pages.waveform-library.spec.ts`
  - 波形库页行为测试

### 可选拆分（实现时再决定）

- 如果 `DashboardPage.vue` 体积迅速增长，可进一步把日志 Tab 区抽成 `frontend/src/components/dashboard/RealtimeLogPanel.vue`
- 如果 `BluetoothStudioPage.vue` 剩余逻辑过重，可先提取共用纯函数到 `frontend/src/utils/bluetooth-studio.ts`

---

### Task 1: 搭建新的后台布局壳与一级导航

**Files:**
- Create: `frontend/src/components/layout/AppSidebarMenu.vue`
- Create: `frontend/src/components/layout/PageHeaderBar.vue`
- Modify: `frontend/src/layouts/AppShell.vue`
- Modify: `frontend/src/styles/app.css`
- Test: `frontend/src/tests/router.spec.ts`

- [ ] **Step 1: 写路由与布局测试草案**

```ts
it("renders sidebar links for dashboard, events and waveforms", async () => {
  router.push("/");
  await router.isReady();
  const wrapper = mount(AppShell, { global: { plugins: [router] } });
  expect(wrapper.text()).toContain("主控台");
  expect(wrapper.text()).toContain("事件配置");
  expect(wrapper.text()).toContain("波形库");
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm run test -- src/tests/router.spec.ts`
Expected: FAIL，因为当前菜单仍是顶部导航，且没有“事件配置 / 波形库”入口

- [ ] **Step 3: 创建最小布局组件**

```vue
<!-- AppSidebarMenu.vue -->
<template>
  <aside class="app-sidebar">
    <RouterLink to="/">主控台</RouterLink>
    <RouterLink to="/events">事件配置</RouterLink>
    <RouterLink to="/waveforms">波形库</RouterLink>
  </aside>
</template>
```

- [ ] **Step 4: 将 `AppShell.vue` 改为左右布局**

```vue
<template>
  <div class="app-shell">
    <AppSidebarMenu />
    <section class="app-main">
      <RouterView />
    </section>
  </div>
</template>
```

- [ ] **Step 5: 在 `app.css` 中加入后台壳样式**

```css
.app-shell {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  min-height: 100vh;
}
```

- [ ] **Step 6: 运行路由测试确认通过**

Run: `npm run test -- src/tests/router.spec.ts`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/layout/AppSidebarMenu.vue frontend/src/components/layout/PageHeaderBar.vue frontend/src/layouts/AppShell.vue frontend/src/styles/app.css frontend/src/tests/router.spec.ts
git commit -m "feat(frontend): 搭建后台布局与一级导航壳" -m "新增左侧一级菜单和统一页面标题栏骨架。`n`n将应用外壳改为左侧菜单加右侧内容区布局，为主控台、事件配置、波形库三页重组做准备。`n`n同步补充路由层测试，约束新导航入口存在。"
```

---

### Task 2: 重组前端路由并兼容旧入口

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `app/api/routes.py`
- Test: `frontend/src/tests/router.spec.ts`
- Test: `tests/test_api_routes.py`

- [ ] **Step 1: 写前后端重定向测试**

```ts
it("redirects legacy command studio route to /events", async () => {
  router.push("/command/studio");
  await router.isReady();
  expect(router.currentRoute.value.fullPath).toBe("/events");
});
```

```python
def test_events_page_prefers_spa_response_when_available(client):
    response = client.get("/events")
    assert response.status_code == 200
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm run test -- src/tests/router.spec.ts`
Expected: FAIL，因为新路由尚未存在  

Run: `pytest tests/test_api_routes.py -q`
Expected: FAIL，因为 FastAPI 还未托管 `/events`

- [ ] **Step 3: 修改前端路由**

```ts
routes: [
  { path: "/", name: "dashboard", component: DashboardPage },
  { path: "/events", name: "events", component: EventConfigPage },
  { path: "/waveforms", name: "waveforms", component: WaveformLibraryPage },
  { path: "/command/studio", redirect: "/events" },
  { path: "/bluetooth/studio", redirect: "/waveforms" },
]
```

- [ ] **Step 4: 修改 FastAPI 路由入口**

```python
@router.get("/events", response_class=HTMLResponse)
async def events_page(...):
    return _spa_index_response("index.html fallback")
```

- [ ] **Step 5: 运行路由与 API 测试确认通过**

Run: `npm run test -- src/tests/router.spec.ts`
Expected: PASS  

Run: `pytest tests/test_api_routes.py -q`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add frontend/src/router/index.ts app/api/routes.py frontend/src/tests/router.spec.ts tests/test_api_routes.py
git commit -m "feat(frontend): 重组路由并兼容旧页面入口" -m "新增事件配置与波形库路由，保留旧的 command 和 bluetooth studio 入口重定向。`n`n同步扩展 FastAPI 的 SPA 托管入口，保证直接访问新路由时仍返回前端产物。"
```

---

### Task 3: 把主控台改造成概览首页

**Files:**
- Create: `frontend/src/components/dashboard/StatusSummaryGrid.vue`
- Create: `frontend/src/components/dashboard/SessionControlPanel.vue`
- Create: `frontend/src/components/dashboard/ConnectionAndDevicesPanel.vue`
- Modify: `frontend/src/pages/DashboardPage.vue`
- Test: `frontend/src/tests/pages.dashboard.spec.ts`

- [ ] **Step 1: 写主控台结构测试**

```ts
it("shows summary cards, session control and runtime logs on dashboard", async () => {
  const wrapper = mount(DashboardPage);
  await flushPromises();
  expect(wrapper.text()).toContain("监听主参数");
  expect(wrapper.text()).toContain("蓝牙设备");
  expect(wrapper.text()).toContain("控制日志");
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm run test -- src/tests/pages.dashboard.spec.ts`
Expected: FAIL，因为当前主控台还是旧的分区结构

- [ ] **Step 3: 提取顶部状态总览**

```vue
<StatusSummaryGrid
  :session="sessionStore.status"
  :command-status="commandStore.status.status"
  :bluetooth-status="bluetoothStore.status.connected ? 'connected' : 'idle'"
/>
```

- [ ] **Step 4: 提取监听控制区**

```vue
<SessionControlPanel
  v-model:session-form="sessionForm"
  :starting-session="startingSession"
  @start="handleStartSession"
  @stop="handleStopSession"
/>
```

- [ ] **Step 5: 提取连接与设备区**

```vue
<ConnectionAndDevicesPanel
  :command-form="commandForm"
  :bluetooth-status="bluetoothStore.status"
  ...
/>
```

- [ ] **Step 6: 保留并下沉事件流面板**

```vue
<ACard title="实时日志">
  <EventStreamTabs :tabs="eventTabs" />
</ACard>
```

- [ ] **Step 7: 运行主控台测试确认通过**

Run: `npm run test -- src/tests/pages.dashboard.spec.ts`
Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add frontend/src/components/dashboard/StatusSummaryGrid.vue frontend/src/components/dashboard/SessionControlPanel.vue frontend/src/components/dashboard/ConnectionAndDevicesPanel.vue frontend/src/pages/DashboardPage.vue frontend/src/tests/pages.dashboard.spec.ts
git commit -m "feat(frontend): 将主控台重组为概览首页" -m "主控台重组为状态总览、监听控制、连接设备和实时日志四个区块。`n`n保留旧前端高频监听参数与启动操作，但移除规则编辑职责，使首页更聚焦于概览和高频控制。"
```

---

### Task 4: 新建事件配置页面并接入 IM Tag

**Files:**
- Create: `frontend/src/pages/EventConfigPage.vue`
- Create: `frontend/src/components/events/EventConfigTabs.vue`
- Create: `frontend/src/components/events/ImRuleGroupsPanel.vue`
- Modify: `frontend/src/pages/CommandStudioPage.vue`
- Test: `frontend/src/tests/pages.event-config.spec.ts`
- Test: `frontend/src/tests/pages.command-studio.spec.ts`

- [ ] **Step 1: 写事件配置页的 IM Tag 测试**

```ts
it("renders IM tag with price rule groups and fixed command ids", async () => {
  const wrapper = mount(EventConfigPage);
  await flushPromises();
  expect(wrapper.text()).toContain("IM");
  expect(wrapper.text()).toContain("礼物");
  expect(wrapper.text()).toContain("固定点赞指令 ID");
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm run test -- src/tests/pages.event-config.spec.ts`
Expected: FAIL，因为页面尚不存在

- [ ] **Step 3: 提取 `CommandStudioPage.vue` 的 IM 规则面板**

```vue
<ImRuleGroupsPanel
  :rules="draftRules"
  :command-slots="commandSlots"
  ...
/>
```

- [ ] **Step 4: 在 `EventConfigPage.vue` 中只接入 IM Tag**

```vue
<EventConfigTabs v-model:active-tab="activeTab" :tabs="tabs" />
<ImRuleGroupsPanel v-if="activeTab === 'im'" ... />
```

- [ ] **Step 5: 保持 `CommandStudioPage.vue` 可作为兼容包装或最小复用页**

```vue
<template>
  <EventConfigPage initial-tab="im" />
</template>
```

- [ ] **Step 6: 运行事件配置与命令规则测试确认通过**

Run: `npm run test -- src/tests/pages.event-config.spec.ts src/tests/pages.command-studio.spec.ts`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add frontend/src/pages/EventConfigPage.vue frontend/src/components/events/EventConfigTabs.vue frontend/src/components/events/ImRuleGroupsPanel.vue frontend/src/pages/CommandStudioPage.vue frontend/src/tests/pages.event-config.spec.ts frontend/src/tests/pages.command-studio.spec.ts
git commit -m "feat(frontend): 创建事件配置页并迁入 IM 规则" -m "新增事件配置页面和标签式规则工作区，先接入 IM 规则编辑与固定指令信息。`n`n同时将旧命令规则页降级为兼容包装入口，为后续合并蓝牙事件规则做铺垫。"
```

---

### Task 5: 将蓝牙事件规则并入事件配置页的蓝牙 Tag

**Files:**
- Create: `frontend/src/components/events/BluetoothEventRulePanel.vue`
- Modify: `frontend/src/pages/EventConfigPage.vue`
- Modify: `frontend/src/pages/BluetoothStudioPage.vue`
- Test: `frontend/src/tests/pages.event-config.spec.ts`
- Test: `frontend/src/tests/pages.bluetooth-studio.spec.ts`

- [ ] **Step 1: 写蓝牙 Tag 测试**

```ts
it("switches to bluetooth tag and shows waveform binding rules", async () => {
  const wrapper = mount(EventConfigPage);
  await flushPromises();
  await wrapper.get('[data-testid="event-tab-bluetooth"]').trigger("click");
  expect(wrapper.text()).toContain("绑定波形");
  expect(wrapper.text()).toContain("互动事件");
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm run test -- src/tests/pages.event-config.spec.ts`
Expected: FAIL，因为蓝牙规则尚未并入

- [ ] **Step 3: 从 `BluetoothStudioPage.vue` 提取蓝牙规则面板**

```vue
<BluetoothEventRulePanel
  :rule-groups="draftRuleGroups"
  :waveforms="draftWaveforms"
  ...
/>
```

- [ ] **Step 4: 在 `EventConfigPage.vue` 接入蓝牙 Tag**

```vue
<BluetoothEventRulePanel v-if="activeTab === 'bluetooth'" ... />
```

- [ ] **Step 5: 将 `BluetoothStudioPage.vue` 降级为兼容包装或仅保留波形相关入口**

```vue
<template>
  <WaveformLibraryPage />
</template>
```

- [ ] **Step 6: 运行事件配置与蓝牙规则测试确认通过**

Run: `npm run test -- src/tests/pages.event-config.spec.ts src/tests/pages.bluetooth-studio.spec.ts`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/events/BluetoothEventRulePanel.vue frontend/src/pages/EventConfigPage.vue frontend/src/pages/BluetoothStudioPage.vue frontend/src/tests/pages.event-config.spec.ts frontend/src/tests/pages.bluetooth-studio.spec.ts
git commit -m "feat(frontend): 合并蓝牙事件规则到事件配置页" -m "将蓝牙事件规则从旧蓝牙 Studio 中拆出并接入事件配置页的蓝牙标签。`n`n页面职责从按技术实现拆分调整为按用户任务拆分，规则配置统一收口到一个工作区中。"
```

---

### Task 6: 新建波形库页面并迁入波形编辑能力

**Files:**
- Create: `frontend/src/pages/WaveformLibraryPage.vue`
- Create: `frontend/src/components/waveforms/WaveformListPanel.vue`
- Create: `frontend/src/components/waveforms/WaveformEditorPanel.vue`
- Modify: `frontend/src/pages/BluetoothStudioPage.vue`
- Test: `frontend/src/tests/pages.waveform-library.spec.ts`
- Test: `frontend/src/tests/pages.bluetooth-studio.spec.ts`

- [ ] **Step 1: 写波形库页面测试**

```ts
it("renders waveform list and editor in dedicated page", async () => {
  const wrapper = mount(WaveformLibraryPage);
  await flushPromises();
  expect(wrapper.text()).toContain("波形库");
  expect(wrapper.text()).toContain("波形编辑器");
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm run test -- src/tests/pages.waveform-library.spec.ts`
Expected: FAIL，因为页面尚不存在

- [ ] **Step 3: 从 `BluetoothStudioPage.vue` 提取波形列表面板**

```vue
<WaveformListPanel
  :waveforms="draftWaveforms"
  :selected-waveform-id="selectedWaveformId"
  @select="selectedWaveformId = $event"
/>
```

- [ ] **Step 4: 提取波形编辑面板**

```vue
<WaveformEditorPanel
  :waveform="selectedWaveform"
  ...
/>
```

- [ ] **Step 5: 组装 `WaveformLibraryPage.vue`**

```vue
<ARow>
  <ACol :xl="8"><WaveformListPanel ... /></ACol>
  <ACol :xl="16"><WaveformEditorPanel ... /></ACol>
</ARow>
```

- [ ] **Step 6: 将旧蓝牙 Studio 路由包装到新页面**

```vue
<template>
  <WaveformLibraryPage />
</template>
```

- [ ] **Step 7: 运行波形库相关测试确认通过**

Run: `npm run test -- src/tests/pages.waveform-library.spec.ts src/tests/pages.bluetooth-studio.spec.ts`
Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add frontend/src/pages/WaveformLibraryPage.vue frontend/src/components/waveforms/WaveformListPanel.vue frontend/src/components/waveforms/WaveformEditorPanel.vue frontend/src/pages/BluetoothStudioPage.vue frontend/src/tests/pages.waveform-library.spec.ts frontend/src/tests/pages.bluetooth-studio.spec.ts
git commit -m "feat(frontend): 拆分独立波形库页面" -m "将波形列表、预览和分段编辑从蓝牙规则工作区中拆出，形成独立的波形库页面。`n`n明确波形资产管理与事件规则配置的边界，降低单页复杂度。"
```

---

### Task 7: 统一页面标题栏动作与视觉节奏

**Files:**
- Modify: `frontend/src/components/layout/PageHeaderBar.vue`
- Modify: `frontend/src/pages/DashboardPage.vue`
- Modify: `frontend/src/pages/EventConfigPage.vue`
- Modify: `frontend/src/pages/WaveformLibraryPage.vue`
- Modify: `frontend/src/styles/app.css`
- Test: `frontend/src/tests/pages.dashboard.spec.ts`
- Test: `frontend/src/tests/pages.event-config.spec.ts`
- Test: `frontend/src/tests/pages.waveform-library.spec.ts`

- [ ] **Step 1: 写标题栏动作测试**

```ts
it("shows page title and primary action in header bar", async () => {
  const wrapper = mount(WaveformLibraryPage);
  await flushPromises();
  expect(wrapper.text()).toContain("波形库");
  expect(wrapper.text()).toContain("新建空白波形");
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm run test -- src/tests/pages.waveform-library.spec.ts`
Expected: FAIL，因为标题栏与主操作尚未统一

- [ ] **Step 3: 为页面标题栏定义统一 props**

```ts
defineProps<{
  title: string;
  description: string;
  actions?: HeaderAction[];
}>();
```

- [ ] **Step 4: 在三个页面接入统一标题栏**

```vue
<PageHeaderBar title="事件配置" description="管理 IM 与蓝牙事件规则">
  <Button>保存规则</Button>
</PageHeaderBar>
```

- [ ] **Step 5: 调整 `app.css` 中内容容器和卡片密度**

```css
.page-content {
  padding: 24px 28px 40px;
}
```

- [ ] **Step 6: 运行页面测试确认通过**

Run: `npm run test -- src/tests/pages.dashboard.spec.ts src/tests/pages.event-config.spec.ts src/tests/pages.waveform-library.spec.ts`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/layout/PageHeaderBar.vue frontend/src/pages/DashboardPage.vue frontend/src/pages/EventConfigPage.vue frontend/src/pages/WaveformLibraryPage.vue frontend/src/styles/app.css frontend/src/tests/pages.dashboard.spec.ts frontend/src/tests/pages.event-config.spec.ts frontend/src/tests/pages.waveform-library.spec.ts
git commit -m "feat(frontend): 统一页面标题栏与内容节奏" -m "为三大一级页面接入统一标题栏、主操作区和内容容器样式。`n`n进一步收敛后台布局的视觉语言，让导航、标题和内容区形成一致的控制台体验。"
```

---

### Task 8: 全量验证、文档同步与收尾

**Files:**
- Modify: `README.md`
- Modify: `docs/使用说明.md`
- Modify: `frontend/src/tests/router.spec.ts`
- Test: `frontend`
- Test: `tests/test_api_routes.py`
- Test: `tests/test_frontend_assets.py`

- [ ] **Step 1: 更新文档中的页面入口说明**

```md
- `/`：主控台
- `/events`：事件配置
- `/waveforms`：波形库
```

- [ ] **Step 2: 补充前端资源与路由断言**

```python
def test_spa_includes_events_and_waveforms_routes():
    ...
```

- [ ] **Step 3: 运行前端全量测试**

Run: `npm run test`
Expected: `6 passed` 或更高，所有 Vitest 用例通过

- [ ] **Step 4: 运行前端构建**

Run: `npm run build`
Expected: Vite build 成功，生成 `dist/`

- [ ] **Step 5: 运行后端回归测试**

Run: `pytest tests/test_api_routes.py tests/test_frontend_assets.py -q`
Expected: PASS

- [ ] **Step 6: 手动联调**

Run: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8010`
Check:
- 左侧一级菜单仅显示 3 个入口
- `/events` 页面存在 `IM / 蓝牙` Tag
- `/waveforms` 页面只展示波形相关内容
- 旧路由可跳转到新页面

- [ ] **Step 7: 提交**

```bash
git add README.md docs/使用说明.md frontend/src/tests/router.spec.ts tests/test_api_routes.py tests/test_frontend_assets.py
git commit -m "docs(frontend): 更新控制台页面结构与入口说明" -m "更新新的页面导航、一级菜单和页面职责说明。`n`n补充前端和后端回归验证，确保控制台布局重组后的入口、静态资源和兼容路由行为稳定。"
```

---

## 计划备注

- 当前 worktree 中已经存在未完成的前端改动和本地配置同步，执行本计划前应先确认这些改动是否作为本重构的一部分继续保留。
- `config/gift_command_mappings.json` 当前已同步主工作区的本地事件规则，实施页面重组时不要误删这份配置。
- 执行时务必遵循 `@superpowers:test-driven-development`，每个页面重组任务都先写失败测试，再做最小实现。
- 页面视觉细化不应先于信息架构重组；先完成路由与职责切分，再做统一视觉收尾。
