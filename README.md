# NIKKE C ARENA Tool

Windows tool for `NIKKE` C ARENA automated screenshots, image stitching, and
battle-image OCR exports. The repository contains both supported products:

- **NIKKE C ARENA Tool (full edition):** automated screenshots, stitching,
  local CPU OCR, optional self-configured NVIDIA GPU OCR, Excel/JSON export,
  and roster maintenance.
- **NIKKE C ARENA Screenshot Tool Lite:** automated screenshots and stitching
  only. Its battle-image recognition page is a visual demo that directs users
  to the full edition.

## Release Files

Installers are published through GitHub Releases, rather than committed to the
Git repository:

- Full edition: `NIKKE_Arena_Tool_Setup_0.1.17.exe`
- Lite edition: `NIKKE_Arena_Capture_Lite_Setup_0.1.9.exe`

## Repository Scope

This repository keeps the application source, installer and update-patch
scripts, required visual resources, OCR parsing logic, and the small offline
model/template files needed to reproduce a release. It deliberately excludes
personal screenshots, OCR results, diagnostics, recovery copies, local Python
runtimes, built installers, and GPU/CUDA runtime components.

The full edition provides optional GPU setup scripts and documentation only.
Users configure any NVIDIA/CUDA/Paddle GPU environment themselves.

Do not bundle NVIDIA CUDA, cuDNN, GPU Paddle runtimes, or other NVIDIA
redistributables into an installer or update patch without an independent,
current license review. Their redistribution conditions are separate from this
project, and bundling them would also substantially increase package size and
create driver/platform compatibility obligations that cannot be validated for
every user environment.

## Getting Started

End users should install a Release package. Developers and contributors should
read [PROJECT_HANDOFF_20260727.md](PROJECT_HANDOFF_20260727.md) and
[PROJECT_DEVELOPER_HANDOFF_20260711.md](PROJECT_DEVELOPER_HANDOFF_20260711.md)
before changing code, rebuilding portable runtimes, or creating a release.

The game should be in fullscreen mode. Screenshot actions send input to the
game window and therefore require launching the tool as administrator.

## Authors

- Product direction and project ownership: **夙辛** (`iiwm5458`)
- Engineering collaboration and packaging support: **Codex (GPT-5)**

Codex is an AI engineering assistant and is credited for its contribution; it
does not claim ownership of the project.

## License and Third-Party Notices

The project's original source code is available under the repository
[LICENSE](LICENSE). `NIKKE` game material, third-party libraries, PaddleOCR
models, icons, and other third-party resources remain subject to their own
licenses and rightsholders' terms.

---

# 中文说明

## 项目简介

`NIKKE C ARENA Tool` 是面向 Windows 的 C ARENA 截图、拼图与战斗图像整理工具。
仓库同时维护两个独立产品：

- **完整版 `NIKKE C ARENA Tool`：** 自动截图、拼图、图像工具、本地 CPU OCR、可选的用户自行配置 GPU OCR、Excel/JSON 导出与妮姬名单维护。
- **轻量版 `NIKKE C ARENA 截图工具 轻量版`：** 自动截图、拼图与图像工具；战斗图像识别页仅用于展示完整版能力。

当前发布版本：完整版 `0.1.17`，轻量版 `0.1.9`。安装包与升级补丁通过 GitHub Releases 发布，不直接提交到 Git 仓库。

## 开发与封装

项目源码、安装器脚本、更新补丁脚本、必要主题资源、OCR 解析逻辑和所需的小型模型/模板均保存在本仓库。接手开发前请先阅读：

1. [PROJECT_HANDOFF_20260727.md](PROJECT_HANDOFF_20260727.md)
2. [PROJECT_DEVELOPER_HANDOFF_20260711.md](PROJECT_DEVELOPER_HANDOFF_20260711.md)

仓库不会提交用户截图、OCR 输出、日志、备份、安装包、Python/Paddle 运行时、CUDA/cuDNN 或 NVIDIA GPU 运行库。完整版的 GPU 配置脚本与文档仅供用户自行配置环境，不随项目分发 GPU 运行时。

### GPU 运行时分发边界

**后续接手者不得将 NVIDIA CUDA、cuDNN、Paddle GPU 运行时或其他 NVIDIA 可再分发组件封装进安装包、升级补丁或 GitHub Release。** 原因如下：

- NVIDIA 组件的最终用户许可与再分发条件独立于本项目；在未进行独立、最新的许可审查前，本项目不应替用户承担再分发责任。
- GPU 运行时会显著增大安装包体积，且可用性依赖用户显卡驱动、Windows 环境与组件版本组合；随包分发也无法保证在每台设备上正常工作。
- 项目仅提供固定版本的一键配置脚本和教程，明确由用户自行下载、安装并确认其 GPU 环境。这样既保留 GPU OCR 能力，也避免将第三方运行库纳入本项目发行物。

## 运行方式与免责声明

本工具通过**可见屏幕画面截图、图像像素识别，以及 Windows 标准鼠标键盘输入**完成操作。

- 本工具不读取、写入或扫描游戏内存；不注入 DLL；不 Hook 游戏进程；不附加调试器；不修改游戏文件、网络通信或客户端数据。
- 本工具的开发初心是方便玩家整理、交流 NIKKE C ARENA 竞技场截图、阵容与对局心得，不提供影响游戏公平性或破坏游戏客户端的功能。
- 请自行确认使用行为符合所在地法律法规、游戏平台规则及游戏运营规则。
- 截图、识别、拼接和自动化结果可能受网络、游戏版本、分辨率或界面变化影响；重要数据请自行复核。
- 本工具按现状提供。因使用、操作失误、设备环境或第三方服务变化造成的损失与争议，使用者应自行承担相应责任。

## 禁止用途

严禁将本工具、其代码、安装包或衍生成果用于读取或篡改他人数据、规避安全机制、制作外挂、侵犯计算机信息系统，或任何其他违法违规用途。用户自行修改、二次分发或违规使用本工具及其衍生成果所产生的后果，由相关行为人自行承担。
