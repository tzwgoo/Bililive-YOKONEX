# Bilibili 直播互动监听面板

一个基于 Python + FastAPI 的本地 Web 面板，支持两种直播消息来源：

- 官方 `open-live`
- 第三方房间消息流 `LiveDanmaku`

两种模式都能实时监听礼物、弹幕、点赞事件；当礼物命中映射规则时，程序会把对应指令发送到 `docs/WEBSOCKET_API.md` 定义的下游 WebSocket 指令通道。

## 环境要求

- Python 3.11+
- Python 3.11+
- 第三方模式：可访问普通 B 站直播间消息流
- 官方模式额外需要：
  - 可访问哔哩哔哩直播开放平台网络
  - `APP_ID`
  - `BILI_ACCESS_KEY_ID`
  - `BILI_ACCESS_KEY_SECRET`
  - 主播身份码 `code`

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置 `.env`

参考 `.env.example` 创建 `.env`：

```env
APP_ID=1234567890123
BILI_ACCESS_KEY_ID=your_access_key_id
BILI_ACCESS_KEY_SECRET=your_access_key_secret
GIFT_MAPPING_PATH=config/gift_command_mappings.json
```

说明：

- `APP_ID` 为开放平台项目 ID
- 主播身份码 `code` 不放在 `.env`，而是在页面中输入
- 第三方模式不依赖这些开放平台字段，如果你只用第三方模式，可以不填写 `.env`
- `GIFT_MAPPING_PATH` 为礼物到指令的映射文件路径
- 下游指令通道参数不再放 `.env`
- 用户需要在页面中手动输入 `WS URL / UID / TOKEN` 并点击“登录指令通道”
- `sendCommand` 需要的 `userId` 会优先使用下游 `loginResult` 返回值
- 如果下游没有返回 `userId`，程序会从页面填写的 `UID` 自动推导，例如 `game_123456` 会自动转成 `123456`

## 配置礼物指令映射

参考 [config/gift_command_mappings.example.json](/D:/BiliLive-YOKONEX/config/gift_command_mappings.example.json) 编辑你的 [config/gift_command_mappings.json](/D:/BiliLive-YOKONEX/config/gift_command_mappings.json)：

```json
[
  {
    "gift_id": 1001,
    "gift_name": "小花花",
    "command_id": "player_hurt"
  }
]
```

规则说明：

- 优先按 `gift_id` 精确匹配
- 如果没有 `gift_id` 命中，再按 `gift_name` 匹配
- 命中后会发送 `sendCommand`，`commandId` 就是配置中的 `command_id`

## 启动服务

```bash
uvicorn app.main:app --reload
```

启动后访问：

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## 打包为 EXE

执行：

```powershell
.\build_exe.ps1
```

产物会输出到：

- `dist/BiliLive-YOKONEX/`

详细使用方式见 [docs/使用说明.md](/D:/BiliLive-YOKONEX/docs/使用说明.md)。

## 使用流程

1. 打开页面，先在“监听模式”里选择：
   - `官方 open-live`
   - `第三方房间消息流`
2. 在“指令通道”区域输入 `WS URL / UID / TOKEN`
3. 点击“登录指令通道”
4. 如果是官方模式，在页面输入主播身份码 `code`
5. 如果是第三方模式，在页面输入直播间房间长 ID `room_id`
6. 点击“启动监听”
7. 观察礼物、弹幕、点赞事件实时刷新，事件卡片会显示消息来源
8. 礼物命中映射后，观察页面中的“最近指令 ID / 最近指令结果”
9. 使用结束后点击“停止监听”

## 联调检查清单

1. 页面能正常打开
2. `/api/status` 返回 `idle`
3. `/api/command/status` 返回 `idle`
4. 页面里手动登录指令通道成功
5. 切换到需要的监听模式
6. 官方模式下输入真实 `code` 后能正常调用 `start`
7. 第三方模式下输入真实 `room_id` 后能正常建立消息流
8. 页面出现房间号、主播昵称、`game_id` 或对应第三方状态
9. 直播间内发送弹幕
10. 页面出现弹幕事件
11. 直播间内点赞
12. 页面出现点赞事件
13. 直播间内赠送礼物
14. 页面出现礼物事件，且命中映射时显示下发结果
15. 下游指令服务收到 `sendCommand`
16. 点击停止后状态回到 `idle`

## 常见问题

### 配置未加载

如果你使用官方模式，请检查 `.env` 是否存在，并确认以下字段已填写：

- `APP_ID`
- `BILI_ACCESS_KEY_ID`
- `BILI_ACCESS_KEY_SECRET`

如果你只使用第三方模式，这个提示不会影响启动第三方监听。

### `7007` 身份码错误

说明主播身份码 `code` 无效或已过期，请重新获取。

### `7003` 心跳过期

说明当前 `game_id` 已失效，需要重新启动监听。

### `7010` 超过连接上限

说明同一直播间下同一应用连接数超限，请先停止旧连接。
