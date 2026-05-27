# 蓝牙波形编辑器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在蓝牙管理页中加入可保存的自定义波形编辑能力，支持新建、复制、编辑、删除自定义波形，并通过鼠标拖拽调整 A/B 通道强度且统一限制到 `0-180`。

**Architecture:** 继续沿用现有 `EmsWaveform` / `EmsWaveformStep` 数据模型，在 `BluetoothService` 和 `BluetoothSettingsStore` 中新增波形 CRUD 与校验能力，通过 FastAPI 路由暴露独立接口。前端在 `bluetooth_studio` 页面新增“波形库 + 编辑器 + 规则区”的组合布局，使用一份草稿状态同时驱动画布拖拽和分段表格。

**Tech Stack:** Python 3.12、FastAPI、Pydantic、原生 JavaScript、Jinja2 模板、pytest

---

## 文件结构与职责

**后端核心**
- 修改: `app/api/routes.py`
- 修改: `app/bluetooth/service.py`
- 修改: `app/bluetooth/storage.py`
- 可能修改: `app/bluetooth/models.py`

**前端页面**
- 修改: `app/templates/bluetooth_studio.html`
- 修改: `app/static/bluetooth_studio.js`
- 修改: `app/static/style.css`

**测试**
- 修改: `tests/test_bluetooth_api.py`
- 修改: `tests/test_bluetooth_service.py`
- 修改: `tests/test_bluetooth_storage.py`
- 修改: `tests/test_frontend_assets.py`

**参考文档**
- 规格: `docs/superpowers/specs/2026-05-26-bluetooth-waveform-editor-design.md`

## 实施原则

1. 先把后端 CRUD 和校验跑通，再搭前端布局。
2. 每个行为先写失败测试，再做最小实现。
3. 只开放 `name`、`duration_ms`、`channel_a`、`channel_b` 编辑。
4. 所有强度在前后端都钳制到 `0-180`。
5. 不直接编辑内置波形，只允许只读查看和复制为自定义。

### Task 1: 扩展 API 合约与后端测试骨架

**Files:**
- Modify: `tests/test_bluetooth_api.py`
- Modify: `app/api/routes.py`

- [ ] **Step 1: 为波形 CRUD 请求模型写失败测试**

```python
def test_bluetooth_waveform_create_endpoint_returns_new_waveform() -> None:
    response = client.post("/api/bluetooth/waveforms", json={"name": "我的波形"})
    assert response.status_code == 200
    assert response.json()["waveform"]["name"] == "我的波形"
```

- [ ] **Step 2: 运行单测确认失败**

Run: `pytest tests/test_bluetooth_api.py -k waveform -v`
Expected: FAIL，提示缺少 `/api/bluetooth/waveforms` 路由或 fake service 对应方法不存在

- [ ] **Step 3: 为 duplicate / update / delete 分别补最小失败测试**

```python
response = client.post("/api/bluetooth/waveforms/ems-preset-01/duplicate", json={})
response = client.put("/api/bluetooth/waveforms/custom-wave-1", json={"name": "新名称", "steps": [...]})
response = client.delete("/api/bluetooth/waveforms/custom-wave-1")
```

- [ ] **Step 4: 在 `routes.py` 中新增最小请求模型占位**

```python
class CreateBluetoothWaveformRequest(BaseModel):
    name: str = ""
```

- [ ] **Step 5: 在 fake service 中补最小方法签名**

```python
def create_waveform(self, *, name: str) -> dict:
    raise NotImplementedError
```

- [ ] **Step 6: 再次运行 API 测试确认失败原因收敛到真实业务未实现**

Run: `pytest tests/test_bluetooth_api.py -k waveform -v`
Expected: FAIL，状态从 404/AttributeError 收敛到业务返回不符

- [ ] **Step 7: Commit**

```bash
git add tests/test_bluetooth_api.py app/api/routes.py
git commit -m "test(蓝牙波形编辑器): 建立波形 CRUD 接口测试骨架"
```

### Task 2: 实现存储层归一化与自定义波形 CRUD

**Files:**
- Modify: `tests/test_bluetooth_storage.py`
- Modify: `app/bluetooth/storage.py`
- Modify: `app/bluetooth/models.py`

- [ ] **Step 1: 为强度上限 180 写失败测试**

```python
def test_store_clamps_custom_wave_strength_to_180(tmp_path) -> None:
    payload = store.load()
    custom_wave = next(item for item in payload.ems_waveforms if item.id == "custom-wave")
    assert custom_wave.steps[0].channel_a == 180
    assert custom_wave.steps[0].channel_b == 180
```

- [ ] **Step 2: 为新建自定义波形的持久化行为写失败测试**

```python
def test_store_save_persists_custom_waveform_round_trip(tmp_path) -> None:
    payload.ems_waveforms.append(...)
    store.save(payload)
    reloaded = store.load()
    assert any(item.id == "custom-wave-1" for item in reloaded.ems_waveforms)
```

- [ ] **Step 3: 运行存储测试确认失败**

Run: `pytest tests/test_bluetooth_storage.py -v`
Expected: FAIL，强度仍未钳制到 180，或新增自定义波形未按预期持久化

- [ ] **Step 4: 将 `_normalize_waveform` 的强度归一化改为 `0-180`**

```python
channel_a=max(0, min(int(step.get("channel_a", 40)), 180))
```

- [ ] **Step 5: 视需要在 `models.py` 添加轻量辅助工厂或拷贝函数**

```python
def clone_waveform_step(step: EmsWaveformStep) -> EmsWaveformStep:
    return EmsWaveformStep(...)
```

- [ ] **Step 6: 运行存储测试确认通过**

Run: `pytest tests/test_bluetooth_storage.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add tests/test_bluetooth_storage.py app/bluetooth/storage.py app/bluetooth/models.py
git commit -m "feat(蓝牙波形编辑器): 补充波形存储归一化与自定义持久化基础"
```

### Task 3: 实现 Service 层波形 CRUD、引用校验与 ID 生成

**Files:**
- Modify: `tests/test_bluetooth_service.py`
- Modify: `app/bluetooth/service.py`
- Modify: `app/bluetooth/models.py`

- [ ] **Step 1: 为 `create_waveform` 写失败测试**

```python
def test_service_can_create_blank_custom_waveform(...) -> None:
    result = service.create_waveform(name="我的波形")
    assert result["waveform"]["builtin"] is False
    assert result["waveform"]["steps"][0]["duration_ms"] == 200
```

- [ ] **Step 2: 为 `duplicate_waveform` 写失败测试**

```python
def test_service_can_duplicate_builtin_waveform(...) -> None:
    result = service.duplicate_waveform(source_waveform_id="ems-preset-01", name="")
    assert result["waveform"]["id"].startswith("custom-wave-")
```

- [ ] **Step 3: 为 `update_waveform` 和“被规则引用禁止删除”写失败测试**

```python
with pytest.raises(ValueError, match="请先修改规则绑定"):
    service.delete_waveform("custom-wave")
```

- [ ] **Step 4: 运行 service 测试确认失败**

Run: `pytest tests/test_bluetooth_service.py -v`
Expected: FAIL，提示缺少 CRUD 方法或返回结构不匹配

- [ ] **Step 5: 在 `BluetoothService` 中实现最小 CRUD**

```python
def create_waveform(self, *, name: str) -> dict:
    waveform = EmsWaveform(...)
    self.payload.ems_waveforms.append(waveform)
    self.store.save(self.payload)
    return {"success": True, "waveform": ..., "waveforms": ...}
```

- [ ] **Step 6: 为 duplicate 复用源 step 底层参数，实现只替换 `id/name/builtin/editable`**

```python
duplicated_steps = [EmsWaveformStep(...copy all fields... ) for step in source.steps]
```

- [ ] **Step 7: 为 delete 增加规则引用检查**

```python
if any(rule.waveform_id == waveform_id for rule in self.payload.bluetooth_event_rules):
    raise ValueError("请先修改规则绑定后再删除该波形")
```

- [ ] **Step 8: 再次运行 service 测试确认通过**

Run: `pytest tests/test_bluetooth_service.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add tests/test_bluetooth_service.py app/bluetooth/service.py app/bluetooth/models.py
git commit -m "feat(蓝牙波形编辑器): 实现波形服务层 CRUD 与引用校验"
```

### Task 4: 打通 FastAPI 路由与 API 层错误映射

**Files:**
- Modify: `tests/test_bluetooth_api.py`
- Modify: `app/api/routes.py`

- [ ] **Step 1: 把 fake service 的 CRUD 返回值补完整**

```python
return {"success": True, "waveform": {...}, "waveforms": [...]}
```

- [ ] **Step 2: 为删除引用冲突和更新非法 payload 写失败测试**

```python
assert response.status_code == 400
assert response.json()["detail"] == "请先修改规则绑定后再删除该波形"
```

- [ ] **Step 3: 运行 API 测试确认失败**

Run: `pytest tests/test_bluetooth_api.py -v`
Expected: FAIL，说明路由或错误映射还未打通

- [ ] **Step 4: 在 `routes.py` 中实现 4 个新接口和请求体结构**

```python
@router.post("/api/bluetooth/waveforms")
async def create_bluetooth_waveform(...):
    ...
```

- [ ] **Step 5: 为 update 请求定义 steps 子模型**

```python
class BluetoothWaveformStepPayload(BaseModel):
    duration_ms: int
    channel_a: int
    channel_b: int
```

- [ ] **Step 6: 统一把 `ValueError` 映射成 400**

```python
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
```

- [ ] **Step 7: 运行 API 测试确认通过**

Run: `pytest tests/test_bluetooth_api.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add tests/test_bluetooth_api.py app/api/routes.py
git commit -m "feat(蓝牙波形编辑器): 暴露波形 CRUD 接口"
```

### Task 5: 搭建管理页编辑器骨架与资源测试

**Files:**
- Modify: `tests/test_frontend_assets.py`
- Modify: `app/templates/bluetooth_studio.html`
- Modify: `app/static/style.css`

- [ ] **Step 1: 为模板结构写失败测试**

```python
assert 'id="studio-waveform-editor"' in studio_html
assert 'id="studio-new-waveform-btn"' in studio_html
assert 'data-action="duplicate-waveform"' in studio_html
```

- [ ] **Step 2: 为样式钩子写失败测试**

```python
assert ".studio-editor-canvas" in style_css
assert ".studio-waveform-card.is-selected" in style_css
```

- [ ] **Step 3: 运行前端资源测试确认失败**

Run: `pytest tests/test_frontend_assets.py -k bluetooth_studio -v`
Expected: FAIL，说明编辑器结构和样式类名尚未出现

- [ ] **Step 4: 修改 `bluetooth_studio.html`，加入编辑器面板与按钮骨架**

```html
<section id="studio-waveform-editor" class="studio-waveform-editor">
  <button id="studio-new-waveform-btn">新建空白波形</button>
</section>
```

- [ ] **Step 5: 修改 `style.css`，补齐三栏布局和选中态样式**

```css
.studio-waveform-card.is-selected { ... }
.studio-editor-canvas { ... }
```

- [ ] **Step 6: 运行资源测试确认通过**

Run: `pytest tests/test_frontend_assets.py -k bluetooth_studio -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add tests/test_frontend_assets.py app/templates/bluetooth_studio.html app/static/style.css
git commit -m "feat(蓝牙波形编辑器): 搭建管理页编辑器骨架"
```

### Task 6: 实现前端波形 CRUD、草稿状态与规则联动

**Files:**
- Modify: `tests/test_frontend_assets.py`
- Modify: `app/static/bluetooth_studio.js`
- Modify: `app/templates/bluetooth_studio.html`

- [ ] **Step 1: 为脚本状态字段和 CRUD 请求入口写失败测试**

```python
assert "let selectedWaveformId" in studio_js
assert 'fetch("/api/bluetooth/waveforms"' in studio_js
assert 'fetch(`/api/bluetooth/waveforms/${waveformId}`' in studio_js
```

- [ ] **Step 2: 为草稿提示和未保存保护钩子写失败测试**

```python
assert "draftDirty" in studio_js
assert "beforeSwitchWaveform" in studio_js
```

- [ ] **Step 3: 运行资源测试确认失败**

Run: `pytest tests/test_frontend_assets.py -k bluetooth_studio -v`
Expected: FAIL，说明脚本尚未具备状态管理和 CRUD 逻辑

- [ ] **Step 4: 在 `bluetooth_studio.js` 中新增编辑器状态与渲染函数**

```javascript
let selectedWaveformId = "";
let draftWaveform = null;
let draftDirty = false;
```

- [ ] **Step 5: 实现新建、复制、保存、删除的最小 fetch 流程**

```javascript
await fetch("/api/bluetooth/waveforms", { method: "POST", ... });
```

- [ ] **Step 6: 实现只读内置波形与可编辑自定义波形的 UI 分支**

```javascript
const isReadonly = Boolean(draftWaveform?.builtin);
```

- [ ] **Step 7: 保存成功后刷新列表并同步规则下拉**

```javascript
studioWaveforms = payload.waveforms || [];
renderWaveformLibrary(studioWaveforms);
renderRuleGroups(currentRuleGroups);
```

- [ ] **Step 8: 运行资源测试确认通过**

Run: `pytest tests/test_frontend_assets.py -k bluetooth_studio -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add tests/test_frontend_assets.py app/static/bluetooth_studio.js app/templates/bluetooth_studio.html
git commit -m "feat(蓝牙波形编辑器): 实现前端波形 CRUD 与草稿状态"
```

### Task 7: 实现画布拖拽编辑与分段表格联动

**Files:**
- Modify: `tests/test_frontend_assets.py`
- Modify: `app/static/bluetooth_studio.js`
- Modify: `app/static/style.css`

- [ ] **Step 1: 为画布交互函数名和拖拽状态写失败测试**

```python
assert "function renderWaveformEditorCanvas(" in studio_js
assert "activeDragHandle" in studio_js
assert "pointerdown" in studio_js
```

- [ ] **Step 2: 为画布样式类写失败测试**

```python
assert ".studio-editor-handle" in style_css
assert ".studio-editor-grid" in style_css
```

- [ ] **Step 3: 运行资源测试确认失败**

Run: `pytest tests/test_frontend_assets.py -k bluetooth_studio -v`
Expected: FAIL，说明拖拽与画布层尚未实现

- [ ] **Step 4: 实现画布 SVG 或 Canvas 渲染函数**

```javascript
function renderWaveformEditorCanvas(waveform) {
  // render A/B polylines and handles
}
```

- [ ] **Step 5: 实现 pointer 拖拽并把值钳制到 0-180**

```javascript
const nextValue = Math.max(0, Math.min(180, calculatedValue));
```

- [ ] **Step 6: 实现表格输入与画布联动刷新**

```javascript
draftWaveform.steps[index].duration_ms = nextDuration;
renderWaveformEditor();
```

- [ ] **Step 7: 在 CSS 中补齐手柄、网格、悬停、高亮态**

```css
.studio-editor-handle.is-active { ... }
```

- [ ] **Step 8: 运行资源测试确认通过**

Run: `pytest tests/test_frontend_assets.py -k bluetooth_studio -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add tests/test_frontend_assets.py app/static/bluetooth_studio.js app/static/style.css
git commit -m "feat(蓝牙波形编辑器): 支持画布拖拽编辑 A B 强度"
```

### Task 8: 全量回归与收尾

**Files:**
- Modify: `docs/superpowers/plans/2026-05-26-bluetooth-waveform-editor.md`
- Verify: `tests/test_bluetooth_api.py`
- Verify: `tests/test_bluetooth_service.py`
- Verify: `tests/test_bluetooth_storage.py`
- Verify: `tests/test_frontend_assets.py`

- [ ] **Step 1: 运行后端相关测试**

Run: `pytest tests/test_bluetooth_api.py tests/test_bluetooth_service.py tests/test_bluetooth_storage.py -v`
Expected: PASS

- [ ] **Step 2: 运行前端资源测试**

Run: `pytest tests/test_frontend_assets.py -v`
Expected: PASS

- [ ] **Step 3: 如本地能启动应用，手动检查 studio 页面**

Run: `python run_app.py`
Expected: 页面可打开 `/bluetooth/studio`，能看到波形编辑器、规则区和拖拽画布

- [ ] **Step 4: 记录任何实现中新增的实际偏差**

```markdown
- 如果画布最终采用 SVG 而不是 Canvas，在此补充原因
```

- [ ] **Step 5: 最终 Commit**

```bash
git add app/api/routes.py app/bluetooth/service.py app/bluetooth/storage.py app/bluetooth/models.py app/templates/bluetooth_studio.html app/static/bluetooth_studio.js app/static/style.css tests/test_bluetooth_api.py tests/test_bluetooth_service.py tests/test_bluetooth_storage.py tests/test_frontend_assets.py
git commit -m "feat(蓝牙波形编辑器): 支持自定义波形编辑与拖拽调强"
```
