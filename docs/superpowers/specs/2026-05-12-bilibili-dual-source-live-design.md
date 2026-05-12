# Bilibili 双链路直播监听集成设计文档

## 1. 背景

当前项目已经实现了基于哔哩哔哩开放平台 `open-live` 的官方监听链路，具备：

- 官方 `start / heartbeat / end`
- 官方互动长连
- 礼物、弹幕、点赞事件展示
- 礼物命中后通过下游 WebSocket 发送指令

现在需要在保留这套“官方原生版本”的前提下，再集成一套第三方直播间消息流方案，用于直接读取普通直播间的弹幕和礼物消息。

用户已经确认采用 `Nemo2011/bilibili-api` 对应的第三方读取思路，并要求：

- 保留现有官方版本
- 在同一页面中做模式切换
- 官方模式继续使用 `code`
- 第三方模式改为使用 `room_id`
- 共用事件面板与下游指令通道

## 2. 目标

本次设计目标如下：

- 在现有项目中新增“第三方房间消息流”监听模式
- 统一前端入口，使用同一页面切换不同监听模式
- 保留原有官方 `open-live` 链路不变
- 新增第三方链路时不破坏现有礼物指令下发逻辑
- 两条链路都统一输出标准事件模型
- 前端可识别事件来源

## 3. 范围

### 3.1 本次要做

- 页面监听模式切换
- 统一启动接口参数结构
- 抽象通用监听会话接口
- 保留 `OpenLive` 官方实现
- 新增 `ThirdParty` 第三方实现
- 统一事件结构，增加 `source`
- 第三方模式支持弹幕、礼物、点赞事件标准化
- 继续复用当前指令通道登录区与礼物映射

### 3.2 本次不做

- 两种模式并发同时监听
- 多房间同时监听
- 第三方模式登录 B 站账号能力
- 历史事件持久化
- 切换模式时保留多个活跃会话
- 完整封装 `Nemo2011/bilibili-api` 全部直播事件

## 4. 方案概览

采用“同一页面模式切换 + 后端双实现同接口”的方案。

页面只保留一套控制按钮与事件面板，但增加一个监听模式选择器：

- `open_live`
- `third_party`

后端新增一个 `LiveSessionManager` 作为统一总控：

- 负责记录当前模式
- 接收统一启动参数
- 把请求转发给对应实现
- 汇总当前状态返回给前端

## 5. 页面设计

## 5.1 监听模式切换

在页面控制区增加模式选择器：

- 官方 open-live
- 第三方房间消息流

切换行为：

- 选 `open_live` 时显示输入框：
  - `主播身份码 code`
- 选 `third_party` 时显示输入框：
  - `直播间长 ID room_id`

按钮保持统一：

- `启动监听`
- `停止监听`

## 5.2 共用区块

以下区域不按模式拆分：

- 指令通道登录区
- 运行状态区
- 礼物事件流
- 弹幕事件流
- 点赞事件流
- 最近指令结果

## 5.3 来源展示

所有标准化事件都增加 `source` 字段，前端可显示来源标签：

- `open_live`
- `third_party_ws`

这样用户能知道当前收到的礼物或弹幕来自哪条链路。

## 6. 后端架构调整

### 6.1 抽象目标

当前 `LiveSessionService` 已经绑定官方实现，不适合直接扩展模式切换。

需要重构为三层：

1. `OpenLiveSessionService`
2. `ThirdPartyLiveSessionService`
3. `LiveSessionManager`

### 6.2 `OpenLiveSessionService`

保留当前逻辑，继续负责：

- `start(code)`
- 官方 `app/start`
- 官方项目心跳
- 官方长连连接与重连
- 官方事件解析
- `LIVE_OPEN_PLATFORM_INTERACTION_END` 处理

这是现有官方原生链路的保留实现。

### 6.3 `ThirdPartyLiveSessionService`

新增第三方链路实现，负责：

- 接受 `room_id`
- 连接第三方直播间消息流
- 监听直播间消息
- 将原始消息映射为统一事件结构
- 维护第三方链路自己的连接状态与断线恢复

该实现不依赖：

- `app/start`
- `game_id`
- 官方项目心跳

### 6.4 `LiveSessionManager`

对前端暴露统一接口：

- `start(mode, value)`
- `stop()`
- `get_status_payload()`

内部规则：

- `mode=open_live` 时调用 `OpenLiveSessionService.start(code=value)`
- `mode=third_party` 时调用 `ThirdPartyLiveSessionService.start(room_id=value)`
- 停止时只停止当前活动实现
- 状态返回中包含当前模式

## 7. 统一状态模型

前端仍使用现有状态机字段：

- `idle`
- `starting`
- `running`
- `reconnecting`
- `stopping`
- `error`

但状态返回增加：

- `mode`
- `mode_label`
- `source`
- `input_label`
- `input_placeholder`

例如：

```json
{
  "mode": "third_party",
  "mode_label": "第三方房间消息流",
  "status": "running",
  "source": "third_party_ws"
}
```

## 8. 统一事件模型

两条链路最终都输出相同结构：

```json
{
  "source": "open_live|third_party_ws",
  "event_type": "gift|danmaku|like|system",
  "cmd": "事件名",
  "room_id": 123456,
  "open_id": "",
  "uname": "用户名",
  "timestamp": 1714113037,
  "payload": {}
}
```

说明：

- `source`：新增，用于区分来源
- `event_type`：继续用于前端分类
- `payload`：按不同事件放标准化内容

## 9. 第三方事件映射规则

基于第三方直播间常见消息流，先覆盖最关键三类：

### 9.1 弹幕

- 原始事件：`DANMU_MSG`
- 标准事件：
  - `event_type = danmaku`
  - `cmd = DANMU_MSG`
  - `source = third_party_ws`

标准化 `payload`：

- `msg`
- `content`
- `uid`
- `fans_medal_level`（若可得）

### 9.2 礼物

- 原始事件：`SEND_GIFT`
- 标准事件：
  - `event_type = gift`
  - `cmd = SEND_GIFT`
  - `source = third_party_ws`

标准化 `payload`：

- `gift_id`
- `gift_name`
- `gift_num`
- `price`
- `coin_type`
- `total_price`

### 9.3 点赞

优先支持第三方链路中的点赞相关事件，例如：

- `LIKE_INFO_V3_CLICK`
- `LIKE_INFO_V3_UPDATE`
- 或者更高层封装后的点赞事件

若底层库只提供部分点赞事件，则按能获取到的数据尽可能标准化：

- `event_type = like`
- `cmd = 原始事件名`
- `payload.like_count`
- `payload.like_text`

## 10. 指令通道兼容性

礼物映射与下游命令发送逻辑保持不变。

当前礼物派发依赖统一标准事件，因此只要第三方礼物事件最终输出为：

- `event_type = gift`
- `payload.gift_id`
- `payload.gift_name`

就可以继续复用：

- `GiftCommandMapper`
- `GiftCommandDispatcher`
- `CommandSessionService`

不需要对礼物映射文件格式做修改。

## 11. API 设计

### 11.1 统一状态接口

保留：

- `GET /api/status`

新增返回字段：

- `mode`
- `mode_label`
- `input_label`

### 11.2 统一启动接口

原接口：

- `POST /api/session/start`

请求体改为：

```json
{
  "mode": "open_live|third_party",
  "value": "主播身份码或房间号"
}
```

行为：

- `open_live` 时 `value` 为 `code`
- `third_party` 时 `value` 为 `room_id`

### 11.3 停止接口

保留：

- `POST /api/session/stop`

停止当前活动模式对应的监听实现。

### 11.4 指令通道接口

保持不变：

- `GET /api/command/status`
- `POST /api/command/connect`
- `POST /api/command/disconnect`

## 12. 实现文件调整建议

建议引入以下新文件：

```text
app/services/open_live_session.py
app/services/third_party_session.py
app/services/live_session_manager.py
app/third_party/
  __init__.py
  event_mapper.py
  ws_client.py
```

调整现有职责：

- 将现有 `LiveSessionService` 拆为 `OpenLiveSessionService`
- 新增 `ThirdPartyLiveSessionService`
- 由 `LiveSessionManager` 接管统一状态接口

## 13. 风险与约束

### 13.1 第三方库事件结构变化

第三方直播间消息流并非官方开放平台事件格式，字段可能变化。

应对策略：

- 在 `event_mapper` 中集中做字段适配
- 不让前端直接消费第三方原始结构

### 13.2 点赞事件一致性

第三方链路点赞事件未必和官方一样稳定，某些房间可能只有累计点赞更新，没有单次点击事件。

应对策略：

- 首版接受“只要能读取点赞相关消息就展示”
- 字段缺失时允许降级显示

### 13.3 双模式切换状态污染

如果切换模式时未彻底停止旧会话，容易导致事件流混乱。

应对策略：

- 切模式前若已有运行中会话，必须先停止
- `LiveSessionManager` 严格保证同一时间只有一个活动监听实现

## 14. 测试策略

### 14.1 管理层测试

- `LiveSessionManager` 启动时正确分发到不同实现
- 不同模式的参数校验正确
- 停止时只停止当前模式实现

### 14.2 第三方映射测试

- `DANMU_MSG -> danmaku`
- `SEND_GIFT -> gift`
- 点赞事件 -> `like`

### 14.3 API 测试

- `mode=open_live`
- `mode=third_party`
- 前端启动接口请求结构变化

### 14.4 前端测试

- 模式切换后输入标签变化
- 提交启动时带上 `mode/value`
- 事件来源标签渲染

## 15. 验收标准

以下全部满足视为本次集成达标：

- 官方 `open-live` 模式仍可正常使用
- 第三方模式可根据 `room_id` 启动
- 两种模式共用同一页面切换
- 礼物、弹幕、点赞事件都能进入统一事件流
- 礼物命中映射后仍能继续向下游发送指令
- 事件来源可在前端区分
- 全量测试通过
