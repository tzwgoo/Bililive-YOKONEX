# 蓝牙波形编辑器设计

> 日期：2026-05-26
> 主题：在蓝牙管理页中加入可保存的自定义波形编辑能力

## 背景

当前 [bluetooth_studio.html](/D:/BiliLive-YOKONEX/app/templates/bluetooth_studio.html) 只支持查看波形库预览，以及为礼物、点赞、弹幕规则绑定已有波形。用户已经可以看到内置 EMS 波形，但还不能创建、复制、编辑和管理自定义波形。

本次设计目标是在现有“波形与事件规则”独立页面中补齐自定义波形编辑能力，并尽量复用当前后端 `EmsWaveform` / `EmsWaveformStep` 数据结构，避免对运行时与协议层做大规模改动。

## 目标

1. 在独立管理页中支持新建空白自定义波形。
2. 支持从内置预设波形复制一份到自定义波形后再编辑。
3. 支持以“分段 step”为单位编辑波形，每段可调整 `duration_ms`、`channel_a`、`channel_b`。
4. 支持鼠标直接拖拽波形画布中的 A/B 通道强度。
5. 统一限制 A/B 通道强度范围为 `0-180`。
6. 支持保存、删除、重命名自定义波形，并继续用于事件规则绑定。

## 非目标

1. 不支持运行中实时下发编辑结果到设备。
2. 不开放 `channel_a_mode`、`channel_a_frequency`、`channel_a_pulse_width` 及 B 通道对应底层协议参数的 UI 编辑。
3. 不支持自由手绘曲线后自动离散成 steps。
4. 不支持撤销 / 重做。
5. 不支持试听、实时播放、批量导入导出。

## 用户确认过的约束

1. 功能范围限定在独立管理页，不在运行中做临时拖动下发。
2. 编辑模型使用“分段编辑”，而不是固定点数组或自由绘制。
3. 首版只开放 `时长 + A 强度 + B 强度`。
4. 自定义波形来源同时支持“新建空白波形”和“复制现有预设波形”。

## 现状与复用点

### 前端

1. [bluetooth_studio.html](/D:/BiliLive-YOKONEX/app/templates/bluetooth_studio.html) 已有独立页壳子与“波形库 / 事件规则”两栏布局。
2. [bluetooth_studio.js](/D:/BiliLive-YOKONEX/app/static/bluetooth_studio.js) 已能拉取 `/api/bluetooth/studio`，渲染波形库卡片与规则绑定。
3. [style.css](/D:/BiliLive-YOKONEX/app/static/style.css) 已有 studio 页基础样式，可在同一视觉语言下扩展编辑器布局和交互态。

### 后端

1. [models.py](/D:/BiliLive-YOKONEX/app/bluetooth/models.py) 已定义 `EmsWaveform` 和 `EmsWaveformStep`，与目标编辑模型一致。
2. [storage.py](/D:/BiliLive-YOKONEX/app/bluetooth/storage.py) 已支持从配置中读取自定义波形，并与默认波形合并。
3. [service.py](/D:/BiliLive-YOKONEX/app/bluetooth/service.py) 已提供 studio payload 与规则保存能力，可继续承担波形 CRUD 的业务入口。

## 信息架构

管理页维持独立页面，但从原来的“两块内容”调整为“波形管理优先，规则绑定次之”的结构：

1. 左侧：波形库
   展示内置波形与自定义波形卡片。
   每张卡片显示名称、类型、分段数、最大强度和小型预览图。
   交互动作：
   - 内置波形：`查看`、`复制为自定义`
   - 自定义波形：`编辑`、`重命名`、`删除`

2. 右上：波形编辑器
   当前选中的波形在这里被编辑。
   包含名称输入、总时长摘要、分段数摘要、最大强度摘要、保存按钮、新建按钮。

3. 右下：事件规则
   保持现有规则列表与波形下拉绑定逻辑。
   与波形编辑解耦，规则保存仍走单独入口。

## 编辑器交互设计

### 总体形式

编辑器采用“画布拖拽 + 分段表格”的混合模式，两个区域共用同一份内存中的草稿数据。

1. 画布负责强度可视化和鼠标直接拖拽。
2. 表格负责时长输入和精确数值微调。

### 画布区

1. 画布横轴表示时间，按照每段 `duration_ms` 占据相对宽度。
2. 画布纵轴固定为 `0-180`，不根据单个波形动态缩放。
3. A 通道使用橙色线条，B 通道使用蓝色线条。
4. 每个 step 暴露两个可拖拽控制点或手柄，分别控制 `channel_a` 和 `channel_b` 的高度。
5. 鼠标拖拽时实时更新当前 step 的强度值，并同步刷新表格和预览摘要。
6. 值在拖拽过程中立即钳制到 `0-180`。
7. 当前悬停或当前编辑的通道高亮显示，避免 A/B 重叠时难以分辨。

### 分段表格区

每个 step 一行，字段如下：

1. 序号
2. 时长 `duration_ms`
3. A 通道强度
4. B 通道强度
5. 操作列

操作列支持：

1. `复制分段`
2. `删除分段`

编辑器整体支持：

1. `新增分段`
2. `保存波形`
3. `放弃当前草稿修改` 或切换波形前二次确认

默认新增分段值：

1. `duration_ms = 200`
2. `channel_a = 0`
3. `channel_b = 0`

删除约束：

1. 至少保留 1 个分段，不能删成空数组。

### 草稿与切换行为

1. 当前编辑波形卡片需要有选中态。
2. 如果用户修改后尚未保存，编辑器显示“未保存更改”提示。
3. 若切换到另一张波形卡片，前端先提示确认，避免误丢草稿。
4. 新建或复制成功后，自动切换到新生成的自定义波形进入编辑态。
5. 删除当前编辑波形后，编辑器回到空白待选状态。

## 数据模型设计

### 保持现有主模型不变

继续使用：

```python
@dataclass
class EmsWaveform:
    id: str
    name: str
    builtin: bool = False
    editable: bool = True
    execution_mode: str = "fixed"
    loop_count: int = 1
    steps: list[EmsWaveformStep] = field(default_factory=list)
```

```python
@dataclass
class EmsWaveformStep:
    duration_ms: int = 200
    channel_a: int = 40
    channel_a_mode: int = 1
    channel_a_frequency: int = 10
    channel_a_pulse_width: int = 5
    channel_b: int = 40
    channel_b_mode: int = 1
    channel_b_frequency: int = 10
    channel_b_pulse_width: int = 5
```

### 首版允许修改的字段

UI 只允许用户变更：

1. `EmsWaveform.name`
2. `EmsWaveform.steps[].duration_ms`
3. `EmsWaveform.steps[].channel_a`
4. `EmsWaveform.steps[].channel_b`

其他字段处理方式：

1. 新建空白波形时，`execution_mode` 继续设为 `"fixed"`，`loop_count` 继续设为 `1`。
2. 复制波形时，复制源波形的 `execution_mode`、`loop_count` 和所有底层 step 参数。
3. 对于未在 UI 中开放的 step 底层字段，保存时沿用原值；新建时使用现有默认值。

## 波形分类与权限规则

### 内置波形

1. `builtin = true`
2. 允许加载到编辑器中查看，但编辑器处于只读态
3. 不允许直接删除
4. 不允许直接保存覆盖
5. 允许“复制为自定义”

### 自定义波形

1. `builtin = false`
2. 允许编辑名称
3. 允许编辑 steps
4. 允许删除
5. 允许被事件规则绑定

## 校验规则

### 前端校验

提交前拦截以下情况：

1. 波形名称为空
2. 分段数组为空
3. `duration_ms < 1`
4. `channel_a` 不在 `0-180`
5. `channel_b` 不在 `0-180`

### 后端校验

服务层和存储归一化层同时校验：

1. `duration_ms` 最小为 `1`
2. `channel_a` 和 `channel_b` 强制钳制到 `0-180`
3. 自定义波形 `id` 必须存在且唯一
4. 不允许覆盖内置波形 ID
5. 删除波形前检查是否仍被任一事件规则引用
6. 新建和复制时由后端生成新的自定义波形 ID，格式建议为稳定前缀加随机后缀，例如 `custom-wave-<短随机串>`

## API 设计

保留现有接口：

1. `GET /api/bluetooth/studio`
2. `POST /api/bluetooth/rules`

新增波形管理接口：

1. `POST /api/bluetooth/waveforms`
   - 作用：创建空白自定义波形
   - 请求：可选名称；若未提供则使用默认名称
   - 返回：新波形详情 + 最新 waveforms 列表

2. `POST /api/bluetooth/waveforms/{id}/duplicate`
   - 作用：从任意现有波形复制一份自定义波形
   - 请求：可选新名称
   - 返回：复制后的新波形详情 + 最新 waveforms 列表

3. `PUT /api/bluetooth/waveforms/{id}`
   - 作用：保存自定义波形编辑结果
   - 请求：`name`、`steps`
   - 返回：保存后的波形详情 + 最新 waveforms 列表

4. `DELETE /api/bluetooth/waveforms/{id}`
   - 作用：删除自定义波形
   - 限制：若被规则引用则报错
   - 返回：删除成功标记 + 最新 waveforms 列表

### 关于 `/api/bluetooth/studio` 返回结构

继续在现有 payload 中返回：

1. `waveforms`
2. `rule_groups`

无需单独增加页面初始化接口，避免前端首次加载时多一次请求拼装。

## 存储设计

继续使用 [storage.py](/D:/BiliLive-YOKONEX/app/bluetooth/storage.py) 当前的“默认波形 + 自定义波形”合并策略。

存储层需要补充的能力：

1. 强度归一化从当前的 `max(0, value)` 升级为 `max(0, min(value, 180))`
2. 自定义波形新增、更新、删除的持久化方法
3. 删除前引用检查可复用 service 层已有 rules 数据

兼容性要求：

1. 旧配置文件继续可读
2. 旧配置里的自定义波形如果强度大于 180，加载时自动钳制到 180
3. 不需要单独迁移脚本

## 前端状态设计

在 [bluetooth_studio.js](/D:/BiliLive-YOKONEX/app/static/bluetooth_studio.js) 中新增编辑器状态：

1. `studioWaveforms`
2. `selectedWaveformId`
3. `draftWaveform`
4. `draftDirty`
5. `activeDragHandle`

推荐原则：

1. 列表数据与草稿数据分离
2. 只在保存成功后回写列表
3. 规则区和波形编辑区互不共享脏状态

## 错误处理

### 用户可见错误

1. 保存失败时在编辑器附近显示明确提示，不覆盖规则保存提示。
2. 删除被引用波形时提示“请先修改规则绑定后再删除该波形”。
3. 创建或复制失败时提示失败原因，不清空当前编辑内容。

### 草稿保护

1. 接口失败不丢草稿。
2. 用户切换波形时若有未保存变更，需要先确认。

## 测试策略

### 后端测试

在现有蓝牙测试基础上新增：

1. 创建空白自定义波形接口测试
2. 复制内置波形为自定义波形接口测试
3. 更新自定义波形接口测试
4. 删除未被引用自定义波形接口测试
5. 删除被引用自定义波形失败测试
6. `storage.py` 中 `channel_a` / `channel_b` 强度上限 180 钳制测试

### 前端资源测试

在 [test_frontend_assets.py](/D:/BiliLive-YOKONEX/tests/test_frontend_assets.py) 增加断言：

1. 模板中出现编辑器容器、新建按钮、波形卡片操作按钮
2. 脚本中出现拖拽编辑、波形 CRUD 请求入口和草稿状态逻辑
3. 样式中出现编辑器布局、画布样式、选中态和拖拽态样式

### 行为测试边界

首版不要求端到端浏览器自动化测试，但接口与资源层测试必须覆盖关键回归点。

## 实现建议

建议拆成以下实现顺序：

1. 后端先补自定义波形 CRUD 与校验
2. 前端再搭编辑器布局和静态渲染
3. 最后接入拖拽交互和草稿流转
4. 完成后补规则引用删除保护与文案细化

这样可以先让“新建 / 复制 / 保存 / 删除”跑通，再叠加鼠标直接操作波形，降低联调难度。

## 风险与取舍

1. 画布拖拽是首版最复杂的部分，但仅负责强度，不负责时长，可控性较高。
2. 如果后续发现同一画布中 A/B 两个手柄重叠过于难选，可在不改数据模型的前提下增加“当前通道切换”辅助交互。
3. 不开放底层协议参数意味着首版更稳，但也意味着高级用户无法做更深调制；这属于后续扩展，不纳入本次范围。

## 成功标准

当以下场景都成立时，认为本次设计达标：

1. 用户能在 studio 页面新建一个自定义波形。
2. 用户能复制任意内置波形为自定义波形。
3. 用户能通过鼠标拖拽修改 A/B 强度，并通过输入修改每段时长。
4. 所有强度保存后都不会超过 180。
5. 自定义波形保存后能立即出现在规则绑定下拉中。
6. 已被规则绑定的自定义波形不能被误删。
