# Release 发布指南

这份文档用于把 `Bililive-YOKONEX` 发布到 GitHub Releases，并附带 Windows 可执行文件。

## 当前推荐方式

当前仓库已经配置了 GitHub Actions 自动发布工作流。推荐使用“推送 tag 自动发布”：

```bash
git tag v0.1.0
git push origin v0.1.0
```

工作流文件：

- `.github/workflows/release.yml`

它会自动完成：

1. 安装 Python 与项目依赖
2. 运行关键测试
3. 执行 `build_exe.ps1`
4. 打包 `dist/BiliLive-YOKONEX/`
5. 创建同名 GitHub Release
6. 上传 `exe`、默认配置文件和 zip 包

## 发布前检查

发布前建议先完成以下步骤：

1. 拉取最新代码并确认当前分支是 `main`
2. 运行测试
3. 重新构建 `exe`
4. 确认 `dist/BiliLive-YOKONEX/` 目录内容完整
5. 更新 `README.md`、`docs/使用说明.md` 或其他需要同步的说明

推荐命令：

```bash
pytest -v
```

```powershell
.\build_exe.ps1
```

## 建议的版本号规则

建议使用语义化版本号：

- `v0.1.0`：首个可用版本
- `v0.1.1`：小修复
- `v0.2.0`：新增功能但不破坏已有使用方式
- `v1.0.0`：正式稳定版本

## GitHub Release 手动发布流程

如果你暂时不想走自动发布，也可以继续手动发布。

1. 打开仓库主页  
   [https://github.com/tzwgoo/Bililive-YOKONEX](https://github.com/tzwgoo/Bililive-YOKONEX)
2. 点击右侧或顶部的 `Releases`
3. 点击 `Draft a new release`
4. 填写：
   - `Choose a tag`：例如 `v0.1.0`
   - `Release title`：例如 `v0.1.0 首个公开版本`
   - `Describe this release`：填写本次更新内容
5. 上传打包产物
6. 选择是否勾选 `Set as the latest release`
7. 点击 `Publish release`

## 建议上传的文件

建议至少上传以下内容：

- `dist/BiliLive-YOKONEX/BiliLive-YOKONEX.exe`
- 如果你希望用户拿到完整运行目录，也可以把整个 `dist/BiliLive-YOKONEX/` 压缩成 zip 再上传

推荐压缩包命名：

- `Bililive-YOKONEX-v0.1.0-win-x64.zip`

## 推荐的 Release 说明模板

可直接参考下面这段：

```md
## 新增

- 支持官方 open-live 与第三方房间消息流双模式监听
- 支持礼物命中后下发固定指令槽位 `command_one` 到 `command_ten`
- 支持本地 Web 控制台管理监听与指令通道

## 修复

- 修复第三方模式在打包版中的客户端导入问题
- 优化控制台样式与状态展示

## 使用方式

1. 下载发布包
2. 配置 `.env`
3. 编辑 `config/gift_command_mappings.json`
4. 运行 `BiliLive-YOKONEX.exe`
```

## 发布后自检

发布完成后建议检查：

1. Release 页面是否能正常打开
2. Tag 是否正确
3. 下载链接是否有效
4. 上传的 `exe` 或 zip 是否完整
5. README 中的截图、说明和文档链接是否仍然正确

## 后续可选优化

如果后面你希望把发布流程进一步自动化，可以继续做：

- GitHub Actions 自动打包
- 自动创建 tag 和 release
- 自动上传 `exe` 或 zip 产物
- 在 README 里加入版本徽标和下载入口
