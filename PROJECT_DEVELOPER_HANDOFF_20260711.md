# NIKKE C ARENA Tool 开发与交接说明

更新时间：2026-07-11
适用根目录：本文件所在目录
当前作者：夙辛（项目方向与所有权，GitHub：`iiwm5458`）；Codex（GPT-5，AI 工程协作与封装支持）

本文面向接手项目的开发者。请先阅读本文，再改动截图、拼图、OCR 或打包逻辑。项目已经同时维护完整版与轻量版；不要用其中一个版本覆盖另一个。

## 1. 产品边界

| 产品 | 用户入口 | 包含能力 | 不包含能力 |
| --- | --- | --- | --- |
| 完整版 | `run_gui.bat` | 截图、拼图、CPU OCR、可选 GPU OCR、Excel/JSON、妮姬名单 | GPU runtime 不随包分发 |
| 轻量版 | `run_capture_lite.bat` | 截图、拼图、颜色/标签判断 | PaddleCPU/PaddleGPU、OCR 导出、名单维护、赛季一键截图 |

轻量版的“战斗图像识别”页面必须保留为展示页。其选图、卡槽、清除、示例、执行、打开数据目录和名单更新按钮均只能提示用户安装完整版，不能启动 OCR 子进程或创建 OCR 输出。

当前发布安装包：

```text
dist/installer/NIKKE_Arena_Tool_Setup_0.1.5.exe
dist/installer/NIKKE_Arena_Capture_Lite_Setup_0.1.0.exe
```

## 2. 仓库与可复制范围

本仓库允许其他开发者复制、修改和发布**原创源代码**，具体见根目录 [LICENSE](LICENSE)。游戏素材、PaddleOCR 模型、第三方库、站点图标和 NVIDIA 相关组件不因本仓库许可证而自动获得再分发授权；发布者须自行核对其条款。

Git 中应保存源码、资源、离线 Paddle 默认模型、安装器脚本和文档；下列内容故意不提交：

```text
runtime_core/  runtime_cpu/  runtime_gpu/  runtime_python310_base/
wheelhouse_gpu/  work/  dist/  screenshots/
custom_backgrounds/  support_custom_backgrounds/
dataanalysis/arena_ocr_tool/tmp/
dataanalysis/arena_ocr_tool/backups/
```

其中 `group_custom_backgrounds/pixiewall-a1cg6q-3840x2160.jpg` 是打包必需底图，例外地应提交；其他用户自定义 GROUP 底图仍保持忽略。

## 3. 克隆与开发环境

```powershell
git clone https://github.com/<owner>/<repository>.git
cd <repository>
```

开发与打包机器要求：Windows 10/11 x64、PowerShell 5.1 或新版 PowerShell、Python 3.10 x64（仅用于构建 runtime）、Inno Setup 6。GUI 脚本中含中文，所有 `.ps1` 文件须保存为 **UTF-8 with BOM**，否则 Windows PowerShell 5.1 可能显示乱码或解析失败。

构建可搬运 runtime：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_portable_runtimes.ps1 -ReplaceExisting
```

该脚本从 Python.org 下载已校验的 CPython 3.10.8 embeddable 包，使用本机 Python 3.10 安装锁定依赖，并生成：

```text
runtime_core/                 # Python + Pillow，截图/拼图必需
runtime_cpu/                  # CPU PaddleOCR、OpenCV、openpyxl 等
dataanalysis/arena_ocr_tool/models/paddle_default/
```

它还需要本机已存在经验证的 Paddle 默认模型缓存 `%USERPROFILE%\.paddleocr\whl`。首次准备该缓存时，应先在受控开发环境运行一次同版本 PaddleOCR，而不是任意升级依赖版本。

## 4. 运行入口和关键代码

| 领域 | 关键文件 |
| --- | --- |
| 完整版 WPF GUI | `nikke_gui_launcher.ps1` |
| 轻量版 WPF GUI | `nikke_capture_lite_launcher.ps1` |
| GUI 权限启动器 | `nikke_gui_bootstrap.ps1`、`run_gui.bat` |
| 自动截图与拼图 | `nikke_round_stitcher.py` |
| 角色详情截图 | `nikke_character_capture.py` |
| 截图与用户设置 | `nikke_round_config.json` |
| OCR CLI | `dataanalysis/arena_ocr_tool/main.py` |
| OCR 识别器 | `dataanalysis/arena_ocr_tool/recognizer/arena_ocr.py` |
| OCR 业务解析 | `dataanalysis/arena_ocr_tool/recognizer/result_parser.py` |
| Excel / JSON 导出 | `dataanalysis/arena_ocr_tool/recognizer/exporter.py` |
| 妮姬名单与别名 | `dataanalysis/arena_ocr_tool/data/nikke_names.json` |

运行时相对路径必须保持可搬运，禁止引入 Codex 缓存路径、开发者用户名或绝对 Python 路径。完整 GUI 的普通截图优先使用 `runtime_core`；OCR 使用 `runtime_cpu` 或经用户自行配置的 `runtime_gpu`。GPU 运行时由 `setup_gpu_runtime.bat`、`setup_gpu_runtime_cn.bat` 与 `setup_gpu_runtime.ps1` 在用户机器创建，不能随普通安装包分发。

## 5. 不可随意破坏的功能契约

### 自动截图与拼图

- 游戏应全屏运行；截图操作需要管理员权限以向游戏窗口发送输入。
- 16/32 强页签依赖蓝色像素判断；16 强战果按钮依赖紫色像素判断；TOP8 决赛战果按钮依赖粉色像素判断；胜方依赖青色高亮判断。
- 这些判断位于 `nikke_round_stitcher.py`，轻量版也依赖它们。不要为了 OCR 改动或删除。
- “当前赛季全部战斗图像一键截图”只属于完整版，轻量版主界面必须保持隐藏。
- 拼图尺寸、block 间距和标注区以全赛季一键截图输出为基准。其它晋级赛和 TOP8 的对应拼图需要与该基准严格一致。

### OCR 与输出

- 保留单图识别；它将被其它页面复用。
- 四卡槽识别按文件名排序：`64进32全部`、`32进16全部`、`16进8全部`、`TOP8-决赛`。
- 64 进 32 负责建立 64 位选手的昵称、ID、P1-P5 和各自战力；后续轮次以玩家 ID 回填阵容、战力与胜负。
- Excel 的 Sheet2 保存 64 位玩家阵容与战力。不要删改该输出契约而不同时更新导出器和回归样本。
- 战力条识别使用双路径 Paddle recognition-only 复核，目标是避免漏读首位。不要恢复已废弃的纯 CV 数字模板替代方案。
- 自动截图中的标签判断、OCR 辅助判断和拼图逻辑与“手动战斗图像 OCR”是不同边界；修改 OCR 时不要影响自动化截图。

更详细的 OCR 背景请阅读 [OCR_HANDOFF_20260701.md](OCR_HANDOFF_20260701.md) 与 [PACKAGING_HANDOFF_20260710.md](PACKAGING_HANDOFF_20260710.md)。

## 6. 打包与验证

完整版：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_installer.ps1 -Version 0.1.6
```

它会构建 `dist/r_0.1.6`、运行 `tools/verify_release_directory.ps1`，并调用 Inno Setup 6 生成：

```text
dist/installer/NIKKE_Arena_Tool_Setup_0.1.6.exe
```

轻量版：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_capture_lite_installer.ps1 -Version 0.1.1
```

它会构建仅含 `runtime_core` 的目录、运行 `tools/verify_capture_lite_release.ps1`，并生成：

```text
dist/installer/NIKKE_Arena_Capture_Lite_Setup_0.1.1.exe
```

发布前最低验证：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\nikke_gui_launcher.ps1 -Check
powershell -NoProfile -ExecutionPolicy Bypass -File .\nikke_capture_lite_launcher.ps1 -Check
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\verify_release_directory.ps1 -ReleaseRoot .\dist\r_0.1.6
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\verify_capture_lite_release.ps1 -ReleaseRoot .\dist\lite_r_0.1.1
Get-FileHash .\dist\installer\*.exe -Algorithm SHA256
```

完整安装器流程和资源清单见 [installer/README.md](installer/README.md)、[PACKAGE_MANIFEST_20260704.md](PACKAGE_MANIFEST_20260704.md) 与 [LIGHTWEIGHT_CAPTURE_TOOL_PACKAGING_PLAN_20260711.md](LIGHTWEIGHT_CAPTURE_TOOL_PACKAGING_PLAN_20260711.md)。

## 7. 建议的 GitHub 发布流程

1. 保持 `main` 可构建，确认 `git status` 中没有截图、runtime、日志或临时评测文件。
2. 构建并验证完整与轻量两个安装包。
3. 对两个 `.exe` 记录 SHA-256，并在 Release 说明中注明对应版本。
4. 提交源码、打上版本标签，例如 `v0.1.5`；同一 Release 可以附带完整版 `0.1.5` 与轻量版 `0.1.0`，但文件名必须保留各自版本号。
5. 在 GitHub Release 上传两个 `.exe`，不要将安装包、Python runtime 或用户截图直接提交到 Git 历史。

## 8. 协作纪律

- 修改前先阅读相关模块与已有交接文档；不要以重构为名改动稳定截图坐标或 OCR 区域。
- 将 OCR、截图和打包视为三个独立验证面。每次改动至少覆盖触及的那一面。
- 不回滚他人未提交的工作；出现并发改动时，先理解并兼容。
- 新增发布资源、默认底图或依赖时，同时更新构建脚本、验证脚本、安装器和本文档。
- 任何 GPU 分发方案都必须先核对 Paddle 与 NVIDIA 的当前许可；默认方案仍是用户自行一键配置 GPU 环境。
