# Bilibili 控制台 EMS 蓝牙接入设计文档

## 1. 背景

当前 `BiliLive-YOKONEX` 已经具备以下能力：

- 通过 `open_live` 或第三方房间消息流接收直播事件
- 对礼物、点赞、弹幕关键词做事件派发
- 将命中的事件映射为固定指令槽位并发送到下游 WebSocket 指令通道
- 在本地 Web 控制台中统一完成监听、登录、状态查看和事件观察

用户希望参考 `D:\STS2-Link-YOKONEX` 项目中已经落地的 EMS 蓝牙能力，在当前项目中新增完整的 EMS 蓝牙接入方案，而不是只增加一个简单的蓝牙发送按钮。

经确认，本次设计采用以下约束：

- 蓝牙能力运行在 Python 后端，不使用浏览器 `Web Bluetooth`
- 设备兼容范围优先参考 `STS2-Link-YOKONEX` 已覆盖的 EMS 识别逻辑
- 首版覆盖礼物、点赞、弹幕关键词三类直播事件到 EMS 波形的绑定
- 保留当前 WebSocket 指令通道能力，蓝牙能力作为并行新增输出，不替换现有通道

## 2. 目标

本次设计目标如下：

- 在当前项目中新增 EMS 蓝牙扫描、连接、断开和状态查询能力
- 在当前控制台中新增 EMS 设备管理、波形库管理和蓝牙事件绑定区域
- 让礼物、点赞、弹幕关键词事件能够直接触发 EMS 波形输出
- 提供可编辑的 EMS 波形库，并支持从内置预设复制出自定义波形
- 确保蓝牙异常不会影响现有直播监听、事件展示和 WebSocket 指令通道

## 3. 范围

### 3.1 本次要做

- 新增 Python 后端 BLE 子系统
- 新增 EMS 设备识别和协议适配
- 新增 EMS 波形定义、预设波形和自定义波形编辑能力
- 新增直播事件到波形的规则绑定能力
- 在现有控制台页面中新增蓝牙相关管理区块
- 增加蓝牙 API、规则派发、波形模型和前端资产测试

### 3.2 本次不做

- 不接入浏览器侧 `Web Bluetooth`
- 不新增与 EMS 无关的蓝牙设备类型
- 不实现复杂的 BLE 调试诊断页
- 不做多设备同时输出的高级混音编排
- 不替换现有 WebSocket 指令通道
- 不实现两个直播监听模式同时并发运行

## 4. 现状与接入边界

当前项目的主链路已经比较清晰：

- `app/main.py`
  - 负责装配 `EventHub`、`CommandSessionService`、`GiftCommandDispatcher`、`DanmakuCommandDispatcher` 和 `LiveSessionManager`
- `app/services/open_live_session.py`
  - 负责官方 `open-live` 模式
- `app/services/third_party_session.py`
  - 负责第三方房间消息流模式
- `app/services/live_session_manager.py`
  - 负责统一管理当前启用的监听模式和启动参数
- `app/api/routes.py`
  - 对前端暴露当前控制台所需接口
- `app/static/app.js` 与 `app/templates/index.html`
  - 负责当前控制台的交互与展示

因此蓝牙能力不应另起一套独立控制台，而应沿着现有“直播事件 -> 派发器 -> 页面状态/事件流”的结构扩展成“双输出”模式：

- 原有输出：WebSocket 指令通道
- 新增输出：EMS 蓝牙波形执行器

## 5. 推荐方案

采用“后端 BLE 子系统 + 控制台扩展 + 直播事件并行派发”的方案。

### 5.1 方案核心

1. 新增 `app/bluetooth/` 子系统，承载扫描、连接、协议适配、波形执行和规则分发
2. 在现有事件派发节点接入 `bluetooth_dispatcher`
3. 在当前控制台中新增：
   - `EMS 蓝牙连接`
   - `EMS 波形库`
   - `蓝牙事件绑定`
4. 将蓝牙配置和波形配置独立保存，但仍归当前项目管理
5. 蓝牙失败只影响蓝牙功能，不影响直播监听和 WebSocket 指令通道

### 5.2 不采用的方案

- 浏览器层 `Web Bluetooth`
  - 无法保证 Windows 本地长期运行稳定性，也不适合承载完整波形执行
- 只做简单蓝牙发送按钮
  - 不满足“完整 EMS 蓝牙方案”的要求，后续必然返工
- 直接照搬 .NET 工程结构
  - 参考项目是 .NET，本项目是 Python，直接平移会导致维护边界混乱

## 6. 后端架构设计

### 6.1 目录规划

建议新增如下结构：

```text
app/
  bluetooth/
    __init__.py
    api_models.py
    constants.py
    device_classifier.py
    event_rules.py
    waveform_library.py
    protocol/
      __init__.py
      ems_ble_protocol.py
    runtime/
      __init__.py
      ble_client.py
      device_manager.py
      status_models.py
      waveform_executor.py
```

### 6.2 模块职责

#### `device_manager`

负责：

- 扫描 BLE 设备
- 根据广播信息生成扫描结果
- 连接目标设备
- 断开当前设备
- 查询连接状态和设备摘要

它只关心设备生命周期，不直接处理直播事件。

#### `device_classifier`

负责：

- 根据设备名特征、广播服务 UUID、特征 UUID 识别 EMS 设备
- 参考 `STS2-Link-YOKONEX` 的 EMS 识别逻辑输出协议类型

首版按“兼容参考项目已覆盖的 EMS 设备”设计，不做新的设备协议族扩展。

#### `protocol_adapter`

负责：

- 将波形步骤转换为设备可写入的 BLE 数据包
- 把不同 EMS 协议差异隔离在同一层内
- 生成停止输出所需的 stop 数据包

#### `waveform_executor`

负责：

- 读取目标波形步骤
- 按时间顺序持续发送协议包
- 波形结束后补发 stop 包
- 维护运行期活跃来源状态

首版执行策略采用“后触发覆盖前触发”的稳定模式，不引入复杂混音。

#### `bluetooth_dispatcher`

负责：

- 接收统一直播事件
- 读取蓝牙事件规则
- 解析命中的目标波形
- 调用 `waveform_executor` 执行输出

### 6.3 与现有服务的接法

在以下两个服务的事件处理节点增加蓝牙派发：

- `app/services/open_live_session.py`
- `app/services/third_party_session.py`

接入顺序建议保持如下：

1. 直播事件被标准化
2. 继续执行现有礼物/点赞/弹幕 WebSocket 派发逻辑
3. 执行蓝牙规则分发
4. 将包含派发结果的事件写入 `EventHub`

这样做可以最大限度减少对现有行为的破坏。

## 7. 配置与数据模型设计

### 7.1 存储方式

建议新增独立配置文件：

```text
config/bluetooth_settings.json
```

原因：

- 当前项目已经使用 `config/gift_command_mappings.json`
- 蓝牙设置与礼物映射不是同一类数据
- 单独文件更便于备份、导入导出和后续扩展

### 7.2 持久化数据结构

建议配置结构分为以下三部分：

```json
{
  "bluetooth_settings": {},
  "ems_waveforms": [],
  "bluetooth_event_rules": []
}
```

### 7.3 `bluetooth_settings`

建议字段：

- `enabled`
- `scan_timeout_seconds`
- `auto_reconnect`
- `last_connected_device_id`
- `last_connected_device_name`
- `default_target_device_id`

说明：

- 连接状态、电量、当前输出波形等瞬时信息不写回文件，只保存在内存运行时状态中

### 7.4 `ems_waveforms`

每个波形建议包含：

- `id`
- `name`
- `builtin`
- `editable`
- `steps`

每个步骤建议包含：

- `duration_ms`
- `channel_a`
- `channel_b`

约束：

- 内置波形可展示、可复制，但不直接原地覆盖
- 用户可删除自定义波形，但不可删除系统保底默认波形
- 读取配置时要做 `normalize`，自动修复缺失字段和非法值

### 7.5 `bluetooth_event_rules`

每条规则建议包含：

- `id`
- `enabled`
- `event_type`
- `waveform_id`
- `cooldown_seconds`
- `filters`

其中：

- `event_type` 取值首版限定为：
  - `gift`
  - `like`
  - `danmaku`
- `filters` 按事件类型携带额外条件

建议约定：

- 礼物规则可按“全部礼物”或按礼物名 / 价格区间细分
- 点赞规则可直接复用当前点赞触发后的统一事件
- 弹幕规则保留关键词配置，与现有弹幕关键词触发保持一致

## 8. API 设计

建议在 `app/api/routes.py` 中新增以下接口。

### 8.1 状态接口

- `GET /api/bluetooth/status`

返回：

- 蓝牙总开关
- 当前连接状态
- 当前设备摘要
- 最近扫描设备列表
- 当前执行状态

### 8.2 设备接口

- `POST /api/bluetooth/scan`
- `POST /api/bluetooth/connect`
- `POST /api/bluetooth/disconnect`
- `POST /api/bluetooth/refresh`

说明：

- `connect` 请求体至少包含 `device_id`
- `refresh` 用于主动刷新连接状态和电量信息

### 8.3 波形库接口

- `GET /api/bluetooth/waveforms`
- `POST /api/bluetooth/waveforms`
- `PUT /api/bluetooth/waveforms/{waveform_id}`
- `DELETE /api/bluetooth/waveforms/{waveform_id}`
- `POST /api/bluetooth/waveforms/{waveform_id}/copy`
- `POST /api/bluetooth/waveforms/import-heartbeat-preset`

说明：

- 首版明确支持“导入心跳预设副本”
- 编辑和删除只允许作用于可编辑波形

### 8.4 规则接口

- `GET /api/bluetooth/rules`
- `PUT /api/bluetooth/rules/{rule_id}`
- `POST /api/bluetooth/rules/reset-defaults`

说明：

- 首版默认给礼物、点赞、弹幕各生成一组基础规则项
- 规则可禁用，但建议默认使用保守配置，避免误触发设备

## 9. 控制台页面设计

控制台继续使用当前单页结构，不新增独立页面。

### 9.1 `EMS 蓝牙连接`

展示内容：

- 蓝牙功能开关
- 当前连接状态
- 已连接设备摘要
- 扫描结果列表

交互按钮：

- `扫描设备`
- `连接`
- `断开`
- `刷新状态`

### 9.2 `EMS 波形库`

展示内容：

- 波形总数
- 当前波形列表
- 当前选中波形摘要
- 当前步骤列表

交互能力：

- 新增自定义波形
- 复制内置预设
- 删除自定义波形
- 编辑步骤时长
- 编辑 `A/B` 双通道强度
- 调整步骤顺序
- 新增步骤
- 删除步骤

首版采用列表式步骤编辑，不要求实现复杂拖拽图编辑。

### 9.3 `蓝牙事件绑定`

展示内容：

- 礼物规则
- 点赞规则
- 弹幕关键词规则

交互能力：

- 启用 / 停用规则
- 选择绑定波形
- 配置冷却时间
- 编辑关键词或事件细分条件

### 9.4 运行状态联动

当前页面已有定时刷新逻辑：

- `refreshStatus()`
- `refreshCommandStatus()`

蓝牙区建议新增：

- `refreshBluetoothStatus()`

并纳入当前控制台的统一刷新循环。

## 10. 运行时与错误处理

必须保证蓝牙能力不拖垮当前项目主链路。

### 10.1 错误隔离原则

- 扫描失败只更新蓝牙状态和错误消息
- 连接失败不影响监听会话继续运行
- 波形执行失败只记录日志，不阻断当前直播事件流
- 配置读写失败应回退到安全默认值

### 10.2 日志建议

建议新增蓝牙日志命名空间：

- `bili_live.bluetooth.device_manager`
- `bili_live.bluetooth.protocol`
- `bili_live.bluetooth.dispatcher`
- `bili_live.bluetooth.executor`

### 10.3 打包注意事项

当前项目支持打包为 Windows `exe`，因此：

- 依赖库需兼容 Windows
- 需要确认打包脚本能带上 BLE 所需依赖
- 运行时配置路径应继续走当前项目已有的 bundle/runtime 路径解析方式

## 11. 依赖建议

建议引入成熟的 Python BLE 客户端库，例如：

- `bleak`

原因：

- 跨平台维护较成熟
- Windows 本地支持较常见
- 适合异步场景，能与当前 FastAPI / asyncio 结构衔接

首版实际实现前需要确认：

- 目标设备在 Windows 上通过该库可稳定扫描和连接
- 特征写入方式满足 EMS 协议发送需求

## 12. 测试策略

遵循 TDD，先补失败测试，再写实现。

### 12.1 配置与模型测试

- 默认蓝牙配置可正确加载
- 默认内置波形存在
- 波形 `normalize` 会修复缺失字段
- 默认规则覆盖礼物、点赞、弹幕

### 12.2 API 测试

- `GET /api/bluetooth/status`
- `POST /api/bluetooth/scan`
- `POST /api/bluetooth/connect`
- `POST /api/bluetooth/disconnect`
- 波形库读写接口
- 规则接口

### 12.3 规则派发测试

- 礼物事件命中后触发目标波形
- 点赞事件命中后触发目标波形
- 弹幕关键词命中后触发目标波形
- 蓝牙关闭时不触发
- 规则关闭时不触发
- 波形缺失时安全失败

### 12.4 协议与执行器测试

- 波形步骤正确转换为协议包
- 执行结束后自动发送 stop 包
- 连续事件触发时执行器行为稳定

### 12.5 前端资产测试

- 页面包含新增蓝牙模块 DOM
- 前端脚本会请求蓝牙状态接口
- 关键按钮和输入框已挂载

### 12.6 回归测试

必须继续通过现有：

- 直播监听相关测试
- WebSocket 指令通道相关测试
- 礼物 / 点赞 / 弹幕派发相关测试
- 前端资产测试

## 13. 风险与对策

### 13.1 设备协议差异

风险：

- 不同 EMS 设备可能存在特征 UUID、包格式或 stop 行为差异

对策：

- 先按参考项目已覆盖范围实现
- 协议适配集中在 `protocol_adapter`
- 不把协议分支散落到页面或 session 层

### 13.2 Python BLE 运行时不稳定

风险：

- Windows 下扫描、连接、重连行为可能与参考项目不完全一致

对策：

- 运行时逻辑尽量集中到 `device_manager`
- 对真实 BLE I/O 做抽象，单元测试使用 fake client
- 首版优先保证单设备、单连接、单执行链路稳定

### 13.3 页面复杂度上升

风险：

- 当前控制台页面已经承载监听与指令通道，再加入蓝牙后容易变重

对策：

- 保持三个独立卡片分区
- 状态、波形、规则分开展示
- 首版避免做复杂图形编辑器

## 14. 验收标准

以下全部满足视为本次蓝牙接入完成：

- 控制台可扫描并展示参考范围内的 EMS 设备
- 用户可以连接、断开并查看当前 EMS 设备状态
- 控制台可以展示并编辑 EMS 波形库
- 可以导入心跳预设副本并作为自定义波形编辑
- 礼物、点赞、弹幕关键词都可绑定到 EMS 波形
- 事件命中后能触发目标波形执行
- 蓝牙异常不会影响直播监听和 WebSocket 指令通道
- 相关新增测试通过，现有核心测试无回归
