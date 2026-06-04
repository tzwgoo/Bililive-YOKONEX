# 波形编辑器拖拽反馈与分段折叠实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让波形编辑器在保持现有连续时间轴与保存接口不变的前提下，补齐更清晰的拖拽反馈，并把逐行分段配置默认收起。

**Architecture:** 这次实现只收敛在 `WaveformEditorPanel.vue` 组件内部状态与样式层，不改页面层数据结构，也不调整蓝牙波形 API。测试先行，先在 Vitest 里锁住默认折叠、激活态、实时手柄文案和参考线，再做最小实现与样式收口。

**Tech Stack:** Vue 3、TypeScript、Ant Design Vue、Vitest、Vue Test Utils

---

## 文件结构

- Modify: `frontend/src/components/waveforms/WaveformEditorPanel.vue`
  - 负责波形编辑卡片、连续时间轴拖拽、分段逐行表单、折叠开关与拖拽反馈 UI。
- Modify: `frontend/src/tests/components.waveform-editor.spec.ts`
  - 负责锁定连续时间轴、拖拽事件、默认折叠、激活态、动态手柄文案与参考线渲染。
- Verify: `frontend/src/pages/WaveformLibraryPage.vue`
  - 仅确认现有页面接线无需改动；除非新增的组件事件需要页面接收，否则不要触碰。

## 实现约束

- 遵守 `DRY`、`YAGNI` 和 `TDD`，先补失败测试，再写最小实现。
- 不修改蓝牙波形保存接口，不新增 store 字段，不引入 localStorage 记忆。
- 拖拽态只在组件内部维护：`activeSegmentIndex`、`dragField`、`isStepListExpanded`。
- 默认折叠的是“逐行分段表单”，不是时间轴、统计卡片或“新增分段”按钮。

### Task 1: 补齐波形编辑器行为测试

**Files:**
- Modify: `frontend/src/tests/components.waveform-editor.spec.ts`
- Verify: `frontend/src/components/waveforms/WaveformEditorPanel.vue`

- [ ] **Step 1: 先为分段折叠写失败测试**

```ts
it("collapses the step list by default and toggles it on demand", async () => {
  const wrapper = mount(WaveformEditorPanel, {
    props: { waveform, savingWaveform: false },
  });

  expect(wrapper.find('[data-testid="step-list"]').exists()).toBe(false);
  await wrapper.get('[data-testid="toggle-step-list"]').trigger("click");
  expect(wrapper.find('[data-testid="step-list"]').exists()).toBe(true);
});
```

- [ ] **Step 2: 再为拖拽激活态和参考线写失败测试**

```ts
it("marks the active segment and renders a guide line while dragging", async () => {
  const wrapper = mount(WaveformEditorPanel, {
    props: { waveform, savingWaveform: false },
    attachTo: document.body,
  });

  await wrapper.get('[data-testid="waveform-handle-channel-a-0"]').trigger("mousedown", {
    button: 0,
    clientX: 60,
    clientY: 160,
  });

  expect(wrapper.get('[data-testid="timeline-segment-0"]').classes()).toContain("is-active");
  expect(wrapper.find('[data-testid="timeline-guide-line-0"]').exists()).toBe(true);
});
```

- [ ] **Step 3: 为拖拽过程中的动态手柄文案写失败测试**

```ts
it("shows live numeric labels on handles while dragging", async () => {
  const wrapper = mount(WaveformEditorPanel, {
    props: { waveform, savingWaveform: false },
    attachTo: document.body,
  });

  await wrapper.get('[data-testid="waveform-handle-duration-0"]').trigger("mousedown", {
    button: 0,
    clientX: 40,
    clientY: 180,
  });
  window.dispatchEvent(new MouseEvent("mousemove", { clientX: 90, clientY: 180, bubbles: true }));

  expect(wrapper.get('[data-testid="waveform-handle-duration-0"]').text()).toContain("360 ms");
});
```

- [ ] **Step 4: 运行前端组件测试，确认新增断言先失败**

Run: `cd frontend; npm run test -- components.waveform-editor.spec.ts`

Expected: `FAIL`，提示缺少 `data-testid="toggle-step-list"`、激活态 class 或动态文本不匹配。

- [ ] **Step 5: 提交测试基线**

```bash
git add frontend/src/tests/components.waveform-editor.spec.ts
git commit -m "test(frontend): 补充波形编辑器折叠与拖拽反馈测试" -m "为波形编辑器新增分段折叠、激活态、参考线和实时手柄文案的失败测试，先锁定旧版体验对齐目标。"
```

### Task 2: 实现拖拽激活态与实时反馈

**Files:**
- Modify: `frontend/src/components/waveforms/WaveformEditorPanel.vue`
- Test: `frontend/src/tests/components.waveform-editor.spec.ts`

- [ ] **Step 1: 在组件脚本里补本地拖拽展示状态**

```ts
const activeSegmentIndex = ref<number | null>(null);
const dragField = ref<DragField | null>(null);

function startDrag(index: number, field: DragField, event: MouseEvent) {
  activeSegmentIndex.value = index;
  dragField.value = field;
  // 保持现有 dragState 初始化逻辑
}

function stopDrag() {
  activeSegmentIndex.value = null;
  dragField.value = null;
  // 保持现有解绑逻辑
}
```

- [ ] **Step 2: 在时间轴模板里加激活态、测试钩子和参考线**

```vue
<article
  :data-testid="`timeline-segment-${index}`"
  class="timeline-segment"
  :class="{ 'is-active': activeSegmentIndex === index }"
>
  <span
    v-if="activeSegmentIndex === index"
    :data-testid="`timeline-guide-line-${index}`"
    class="timeline-guide-line"
  />
</article>
```

- [ ] **Step 3: 把静态 `A / B / xxx ms` 文案改成拖拽时实时值**

```vue
{{ activeSegmentIndex === index && dragField === "channel_a" ? `A ${step.channel_a}` : "A" }}
{{ activeSegmentIndex === index && dragField === "channel_b" ? `B ${step.channel_b}` : "B" }}
{{ activeSegmentIndex === index && dragField === "duration_ms" ? `${step.duration_ms} ms` : `${step.duration_ms} ms` }}
```

实现要求：
- `A/B` 非拖拽态可保留简短标签。
- 时长按钮始终显示毫秒值，拖拽时只增强样式与实时更新。

- [ ] **Step 4: 给拖拽中高亮、非当前段降噪和手柄激活态补样式**

```css
.waveform-track.is-dragging .timeline-segment:not(.is-active) {
  opacity: 0.58;
}

.timeline-segment.is-active {
  background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(255,247,237,0.98));
}

.timeline-handle.is-active,
.timeline-duration-handle.is-active {
  box-shadow: 0 14px 28px rgba(28, 25, 23, 0.22);
  transform: translateY(50%) scale(1.04);
}
```

- [ ] **Step 5: 运行组件测试，确认反馈相关断言通过**

Run: `cd frontend; npm run test -- components.waveform-editor.spec.ts`

Expected: `PASS`，新增的激活态、参考线和动态文案测试全部通过。

- [ ] **Step 6: 提交最小拖拽反馈实现**

```bash
git add frontend/src/components/waveforms/WaveformEditorPanel.vue frontend/src/tests/components.waveform-editor.spec.ts
git commit -m "feat(frontend): 增强波形编辑器拖拽反馈" -m "为连续时间轴补充分段激活态、参考线、手柄激活样式和实时数值反馈，让拖拽体验更接近旧版前端。"
```

### Task 3: 实现分段配置默认折叠

**Files:**
- Modify: `frontend/src/components/waveforms/WaveformEditorPanel.vue`
- Test: `frontend/src/tests/components.waveform-editor.spec.ts`

- [ ] **Step 1: 在组件脚本里新增折叠状态，默认收起**

```ts
const isStepListExpanded = ref(false);

function toggleStepList() {
  isStepListExpanded.value = !isStepListExpanded.value;
}
```

- [ ] **Step 2: 在工具栏添加折叠切换按钮**

```vue
<div class="step-toolbar">
  <Button size="small" @click="toggleStepList" data-testid="toggle-step-list">
    {{ isStepListExpanded ? "收起分段配置" : "展开分段配置" }}
  </Button>
  <Button size="small" :disabled="waveform.builtin" @click="emit('add-step')">新增分段</Button>
</div>
```

- [ ] **Step 3: 只在展开时渲染逐行分段表单**

```vue
<div v-if="isStepListExpanded" data-testid="step-list" class="step-list">
  <!-- 保持现有 step-row 结构 -->
</div>
```

- [ ] **Step 4: 收紧折叠后的间距与工具栏布局**

```css
.step-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
```

实现要求：
- 折叠后页面不出现空白占位。
- “新增分段”按钮始终可见，避免主路径被折叠。

- [ ] **Step 5: 运行组件测试，确认默认折叠和切换通过**

Run: `cd frontend; npm run test -- components.waveform-editor.spec.ts`

Expected: `PASS`，默认折叠与展开切换测试通过，原有拖拽测试继续通过。

- [ ] **Step 6: 提交折叠交互实现**

```bash
git add frontend/src/components/waveforms/WaveformEditorPanel.vue frontend/src/tests/components.waveform-editor.spec.ts
git commit -m "feat(frontend): 默认收起波形分段配置" -m "将逐行分段表单改为默认折叠，并提供明确的展开与收起入口，降低波形库页面初始信息密度。"
```

### Task 4: 联调验证与收尾

**Files:**
- Verify: `frontend/src/components/waveforms/WaveformEditorPanel.vue`
- Verify: `frontend/src/pages/WaveformLibraryPage.vue`
- Verify: `frontend/src/tests/components.waveform-editor.spec.ts`

- [ ] **Step 1: 运行完整前端测试集**

Run: `cd frontend; npm run test`

Expected: `PASS`，不只 `components.waveform-editor.spec.ts`，其他页面和组件测试也保持通过。

- [ ] **Step 2: 运行前端构建**

Run: `cd frontend; npm run build`

Expected: `PASS`，Vite 正常产出，无 TypeScript 或模板编译错误。

- [ ] **Step 3: 本地手动验证波形库页**

Run: `cd frontend; npm run dev`

Manual checklist:
- 初次进入波形库时，逐行分段配置默认收起。
- 拖 A/B 手柄时，当前段高亮且能看到实时数值。
- 拖时长手柄时，毫秒文案随拖拽变化。
- 展开分段配置后，数值输入与复制/删除分段仍可用。

- [ ] **Step 4: 检查页面层是否无需额外改动**

Run: `rg -n "WaveformEditorPanel|toggle-step-list|step-list" frontend/src`

Expected: 只有波形编辑组件和测试需要改；如果页面层没有新增接线需求，就不要扩大范围。

- [ ] **Step 5: 生成最终提交**

```bash
git add frontend/src/components/waveforms/WaveformEditorPanel.vue frontend/src/tests/components.waveform-editor.spec.ts
git commit -m "refactor(frontend): 打磨波形编辑器默认视图与拖拽反馈" -m "对齐旧版前端的波形编辑体验，补齐拖拽激活反馈并将逐行分段配置默认收起，同时保持现有数据结构和保存接口不变。"
```

## 备注

- 如果拖拽文案在极窄分段里出现遮挡，优先通过缩小字号、增强选中段最小宽度或在激活态显示紧凑文案解决，不要顺手扩展到重新设计整个时间轴。
- 如果测试里需要稳定拖拽数值，继续使用 `getBoundingClientRect` mock，避免把 flaky 行为引入 Vitest。
