# NIKKE 工具封装交接文档

更新时间：2026-07-10
项目根目录：`C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs`

本文交给后续负责“封装、安装器、发布包验证”的 Codex 对话。目标是研究并实施可靠的 Windows 发布方案；不要借封装之名改动已经稳定的自动截图、拼图和 OCR 识别逻辑。

## 1. 当前产品与发布目标

这是《胜利女神：新的希望 / NIKKE》C ARENA 工具，包含：

- PowerShell WPF GUI、自动截图、拼图、背景板输出。
- 手动上传战斗数据截图的 OCR，导出 Excel 与 JSON。
- 本地妮姬名单维护、收藏品、循环等级、胜负、战力识别。
- CPU PaddleOCR 与可选 NVIDIA GPU PaddleOCR。
- OCR 温度保护、进度展示、暂停/终止控制；只作用于手动战斗图像 OCR，不影响自动截图流程。

用户的发布要求是支持三种使用形态：

1. **仅截图工具**：不安装任何 OCR runtime，自动截图、拼图和其他非 OCR 功能仍可用。
2. **CPU OCR**：适合所有 Windows 用户，作为推荐的通用 OCR 选项。
3. **GPU OCR**：仅 NVIDIA GPU 用户可选；可与 CPU OCR 共存。

因此，发布器应当把“核心截图工具”“CPU OCR”“GPU OCR”做成可独立选择的组件，而不是假定所有用户都有 GPU 或 Python 环境。

**截图 worker 也通过 Python 执行。** 已实现并验证 `runtime_core\python.exe`：它是完整可复制的 CPython 3.10.8 embeddable runtime，包含 Pillow、只服务自动截图和拼图。`runtime_cpu\python.exe` 是独立完整的 CPU OCR runtime。两者都不含 `pyvenv.cfg`，`sys.prefix` 与 `sys.base_prefix` 都指向自身目录；因此“仅截图工具”可以不安装 CPU OCR 组件。

## 2. 当前架构：不要误判成单一 Python 程序

主用户入口：

```text
run_gui.bat
  -> powershell.exe -File nikke_gui_launcher.ps1
  -> PowerShell WPF GUI
  -> 启动 Python 子进程执行截图或 OCR
```

关键文件：

| 作用 | 文件 |
| --- | --- |
| GUI 主程序 | `nikke_gui_launcher.ps1` |
| GUI 启动入口 | `run_gui.bat` |
| 自动截图与拼图 | `nikke_round_stitcher.py` |
| 角色详情截图 | `nikke_character_capture.py` |
| OCR CLI 入口 | `dataanalysis/arena_ocr_tool/main.py` |
| OCR wrapper | `dataanalysis/arena_ocr_tool/recognizer/arena_ocr.py` |
| OCR 业务解析 | `dataanalysis/arena_ocr_tool/recognizer/result_parser.py` |
| OCR 输出 | `dataanalysis/arena_ocr_tool/recognizer/exporter.py` |
| 本地妮姬名单/别名 | `dataanalysis/arena_ocr_tool/data/nikke_names.json` |
| 截图和 GUI 配置 | `nikke_round_config.json` |

**建议的第一版封装形态：目录型发布包加安装器，而不是把所有东西强行压成单个 PyInstaller EXE。**

理由：GUI 本身是 PowerShell WPF，且会按不同模式调用独立的 CPU/GPU Python runtime；PaddleOCR、OpenCV、模型资源和 CUDA DLL 都不适合先在没有验证的情况下做单文件冻结。可以使用 Inno Setup、NSIS 或等价安装器安装一个完整目录，再由快捷方式启动 `run_gui.bat` 或一个很薄的启动器。是否要在后续把截图 worker 单独打包为 EXE，应作为独立课题验证，不能阻塞第一版目录型发布。

## 3. Runtime 与组件选择

### 3.1 CPU OCR

当前开发环境已有：

```text
runtime_cpu\python.exe
Python 3.10.8
paddlepaddle==2.6.2
paddleocr==2.7.3
numpy==1.26.4
opencv-python-headless==4.9.0.80
rapidfuzz
lxml
openpyxl
Pillow
```

依赖清单：`dataanalysis/arena_ocr_tool/requirements-ocr.txt`；可复现构建使用完整锁定文件 `dataanalysis/arena_ocr_tool/requirements-ocr-cpu.lock.txt`。

当前 `runtime_core` 约 31 MB，`runtime_cpu` 约 974 MB。截图启动器已优先使用 `runtime_core`，CPU OCR 仍优先使用 `runtime_cpu`。未选择 CPU OCR 时，GUI 应继续作为截图工具运行，并清楚提示 OCR 未安装。

### 3.2 GPU OCR

当前验证组合：

```text
Python 3.10 64-bit
paddlepaddle-gpu==2.6.2
paddleocr==2.7.3
numpy==1.26.4
opencv-python-headless==4.9.0.80
nvidia-cuda-runtime-cu11==11.8.89
nvidia-cuda-nvrtc-cu11==11.8.89
nvidia-cublas-cu11==11.11.3.6
nvidia-cudnn-cu11==8.9.5.29
```

依赖清单：`dataanalysis/arena_ocr_tool/requirements-ocr-gpu.txt`。安装脚本与用户教程已存在：

```text
setup_gpu_runtime.bat
setup_gpu_runtime_cn.bat
setup_gpu_runtime.ps1
GPU_OCR_RUNTIME_SETUP_GUIDE.md
```

GPU runtime 目前约 4.3 GB。普通社区发布包**不建议内置** `runtime_gpu/` 或 `wheelhouse_gpu/`：体积过大，并涉及 Paddle GPU 与 NVIDIA CUDA/cuDNN 第三方运行库的再分发许可问题。应当保留 GPU 安装脚本，让用户自行下载并确认第三方条款。

GPU 安装前提：Windows 64-bit、NVIDIA 显卡及驱动、`nvidia-smi` 可用、Python 3.10 64-bit。脚本会创建 `runtime_gpu/` 并写入 `sitecustomize.py`，为 CUDA/cuDNN DLL 注册搜索目录。不要删除这段 DLL 注册逻辑。

### 3.3 GUI 的 runtime 发现顺序

`nikke_gui_launcher.ps1` 已实现 runtime 探测：

- 非 OCR 截图 Python：优先 `runtime_core\python.exe`，其次 `runtime_cpu\python.exe` 与本机 Python。
- CPU OCR：`NIKKE_OCR_PYTHON`、内置 `runtime_cpu`、本机 Python。
- GPU OCR：`NIKKE_OCR_GPU_PYTHON`、内置 `runtime_gpu`；还必须通过 `paddle.device.is_compiled_with_cuda()` 和 GPU 数量校验。

封装后必须保留这些相对路径与环境变量覆盖能力，不可重新引入任何 Codex、开发者用户名或绝对 Python 路径。

### 3.4 可搬运 runtime 的重建方式

构建脚本：`tools/build_portable_runtimes.ps1`。

它会从 Python.org 的 CPython 3.10.8 64-bit embeddable 包构建 `runtime_core` 与 `runtime_cpu`，再将验证过的默认模型复制到项目资源目录。CPU runtime 使用 `requirements-ocr-cpu.lock.txt`，避免间接依赖漂移。构建会先在 `work/portable_runtime_build/` 验证导入，只有成功才替换目标目录；旧 runtime 会移到该目录的 `backups/` 中。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_portable_runtimes.ps1 -ReplaceExisting
```

构建脚本只供开发/发布环境使用，`runtime_core/`、`runtime_cpu/` 和 `work/` 都由 `.gitignore` 排除；发布构建器必须明确复制两个 runtime，而不是依赖 Git 跟踪它们。

## 4. 必须解决的发布前问题

### 4.1 PaddleOCR 默认模型已离线化

`recognizer/arena_ocr.py` 现已为主中文 reader 和日/韩昵称 reader 显式传入项目内模型目录：

```text
dataanalysis/arena_ocr_tool/models/paddle_default/
```

该目录约 21 MB，包含中文检测、中文识别、方向分类和多语言检测模型。昵称额外使用的日文/韩文 recognition-only 模型仍在项目内：

```text
dataanalysis/arena_ocr_tool/models/nickname/japan/
dataanalysis/arena_ocr_tool/models/nickname/korean/
```

验证已将 `HOME` 与 `USERPROFILE` 指向空目录：主 reader、日文昵称 reader、韩文昵称 reader 均成功初始化，并且没有创建 `.paddleocr`。这项验证证明运行时模型初始化不依赖用户缓存或首次联网下载；仍需在干净 Windows 机器运行完整单图和四图 OCR 回归。

### 4.2 默认配置不能沿用开发机偏好

当前开发机 `nikke_round_config.json` 的 `launcher_settings` 显示 GPU 与性能优先模式，这属于本机状态，不能直接作为普通发布默认值。

发布模板应至少满足：

- 没有 GPU runtime 时绝不默认选择 GPU。
- 默认热保护模式为 `safe`，而不是性能优先。
- 若发布包没有 CPU OCR 组件，GUI 应正常作为截图工具运行，并清楚提示如何安装 OCR。
- 用户更新名单、主题、性能设置等产生的可写配置应与只读程序资源分离，避免安装到 `Program Files` 后写入失败。

### 4.3 管理员权限和安装路径

自动截图需要向游戏窗口发送输入，因此 GUI 需要管理员权限。发布方案应提供清晰的 UAC 提升路径，而不是要求用户手工右键 PowerShell 脚本。

同时，截图、Excel、JSON、日志、用户自定义底图和名单均会写入磁盘。不要把可写目录放在只读安装目录。可选方案：

- 便携版：用户自己选择可写目录，程序目录内可写。
- 安装版：程序放在安装目录；可写数据放 `%LOCALAPPDATA%\NIKKE_Arena_Tool\`，并让 GUI 统一解析该数据根目录。

这会影响现有相对路径逻辑，修改前必须做完整回归，不能只改某一个脚本。

## 5. 必须随包携带的资源

安全起见，第一版 CPU OCR 组件应整体保留以下目录，而不是尝试按文件名“瘦身”：

```text
assets/
vendor/LibreHardwareMonitorLib/
dataanalysis/arena_ocr_tool/recognizer/
dataanalysis/arena_ocr_tool/data/
dataanalysis/arena_ocr_tool/models/
dataanalysis/arena_ocr_tool/main.py
runtime_cpu/                         （仅选择 CPU OCR 时）
```

其中：

- `assets/`：GUI 背景、图标、底图等，当前约 56 MB。
- `vendor/LibreHardwareMonitorLib/`：温度传感器读取依赖；缺失时 UI 应降级，但不能崩溃。
- `data/nikke_names.json` 与 `data/nikke_names.backup.json`：本地名单及备份，必须一起保留。
- `data/collection_cv_templates/` 与 `data/collection_templates/`：收藏品 CV 模板和兼容模板；当前运行代码依赖其内容。
- `models/nickname/japan/`、`models/nickname/korean/`：日文/韩文昵称 OCR 模型，懒加载但对识别准确率重要。

妮姬名单只能从本地 JSON/本地备份恢复；不要重新加入从 GameKee 或其他网站自动拉取名单的代码，以避免用户担心程序被误认为攻击网站。

## 6. OCR 当前稳定点：封装不得破坏

### 6.1 识别范围

OCR 支持单张战斗数据图和完整四卡槽赛季图：

```text
64进32全部战斗数据（详）
32进16全部战斗数据（详）
16进8全部战斗数据（详）
TOP8-决赛战斗数据（详）
```

四图模式按文件名自动排序。64 进 32 会识别并建立 64 位玩家阵容；后续轮次回填阵容数据。

### 6.2 已验证的战力规则

CPU 和 GPU Paddle 路径现在都使用同一套战力条复核：

- 每个玩家侧有 5 个阵容，每阵容 5 个战力槽，共 25 个战力条小图。
- 原始战力条和预处理战力条分别批量 recognition-only 识别。
- 两次读数一致才作为战力条候选；较短候选不能覆盖已有较长数值。
- 默认由 `NIKKE_POWER_STRIP_VERIFY=auto` 启用；`off` 才关闭。
- 战力有效范围：`10000-199999` 正常；`200000-299999` 可疑复核；`300000-400000` 高风险；大于 `400000` 无效。

GPU 五种分辨率的 8,000 个战力槽已对基准表验证为 0 差异。CPU 对真实 3440 图片 25 个槽位小样本验证为双读一致且全对。CPU 仍会比旧路径多一次复核，批量执行是为了避免逐槽重复调用模型。

不要恢复已经验证失败的“纯数字 CV 模板替换 Paddle”方案。历史和回滚材料在：

```text
dataanalysis/arena_ocr_tool/backups/POWER_OCR_ATTEMPTS_20260708.md
dataanalysis/arena_ocr_tool/backups/power_strip_recognition_only_20260710_065218/
dataanalysis/arena_ocr_tool/backups/cpu_power_roster_headers_20260710_095338/
```

### 6.3 名称、收藏品、胜负、循环等级

- 名称识别依赖本地名单、安全别名、阵容槽与详细赛果页的交叉验证。包含冒号或长度至少 5 的名称需保留槽位级升级逻辑；用户新增名称会自动参与该规则。
- 收藏品等级：`无、R、R15、SR、SR15、SSR、SSR3`。`SSR3` 是历史 `SSR15` 的新名称。收藏品 CV 模板必须随包保留。
- 只有在“珍藏品名单”中的妮姬允许识别为 `SSR` 或 `SSR3`；即使角色在该名单中，空槽也必须正确判为“无”。
- 详细赛果页通过“战败”贴图和文字识别胜负；简化赛果页使用独立的 WIN/LOSE/颜色逻辑。不要把二者混成同一规则。
- 循环等级仅读取底部八个数值：极乐净土、泰特拉、米西利斯、朝圣者、反常、火力型、防御型、辅助型。

### 6.4 输出契约

Excel：

- `ArenaData`：逐局数据，攻守双方 `P1-P5` 仍表示**一局阵容中的五个卡槽**，不得重命名。
- `参赛阵容`（第二个 Sheet）：按玩家汇总的五个阵容，表头为：

```text
参赛选手、选手ID、阵容1、阵容1战力、阵容1收藏、...、阵容5、阵容5战力、阵容5收藏、八项循环等级
```

JSON：

- `{stem}_result.json`：逐局数据，保持既有 P1-P5 槽位语义。
- `{stem}_roster.json`：与第二个 Sheet 对应的玩家阵容汇总，使用“阵容1...阵容5”字段。

封装测试不能只检查程序退出码，应打开导出的 xlsx/json 检查这份契约。

## 7. 温度保护与性能边界

已有设计和代码：`OCR_PERFORMANCE_THERMAL_PROTECTION_PLAN_20260703.md`、`nikke_gui_launcher.ps1`、`main.py` 中的 `OcrRunControl`。

- 只针对 GUI 手动启动的战斗图像 OCR。
- 安全模式会在每个对局 block 后短暂 sleep，可按温度延长或暂停；性能模式不主动降速，但保留硬阈值暂停。
- GUI 与 Python OCR 子进程通过 progress JSON 和 control JSON 协作，允许停止、暂停、恢复。
- 温度传感器不可读时必须降级，不得导致 OCR 或 GUI 崩溃。
- 不要把该控制逻辑接入自动截图、窗口定位或自动拼图。

封装时保留 `LibreHardwareMonitorLib` 和 `nvidia-smi` 的可选读取逻辑；没有传感器/没有 NVIDIA GPU 的普通电脑仍必须能运行 CPU OCR。

## 8. 推荐发布目录与排除项

建议由安装器生成类似结构：

```text
NIKKE_Arena_Tool/
  run_gui.bat
  nikke_gui_launcher.ps1
  nikke_round_stitcher.py
  nikke_character_capture.py
  nikke_round_config.json
  nikke_character_capture_config.json
  assets/
  vendor/
  dataanalysis/arena_ocr_tool/
  runtime_core/                 已验证的纯截图 Python/Pillow runtime
  runtime_cpu/                  已验证的独立 CPU OCR runtime
  setup_gpu_runtime*.bat/.ps1   始终保留，供用户自主安装 GPU
  docs/
  screenshots/                  首次启动创建的可写目录或数据目录
  custom_backgrounds/
  support_custom_backgrounds/
  group_custom_backgrounds/
```

普通用户包应排除或不随安装器安装：

```text
runtime_gpu/
wheelhouse_gpu/
screenshots/ 的历史图片和结果
dataanalysis/arena_ocr_tool/tmp/
dataanalysis/arena_ocr_tool/backups/
dataanalysis/arena_ocr_tool/tools/evaluate_*.py
manual_annotations、历史 OCR 调试图、开发测试 PNG
__pycache__/
Codex 交接资料（开发包可保留）
```

发布前先做资源审计；若因为离线默认模型方案新增 Paddle 模型目录，不得被上述排除规则误删。

## 9. 需要后续 Codex 决策/实施的事项

1. 已选用 Inno Setup 6：`installer/NIKKE_Arena_Tool.iss` 支持核心截图组件必装、CPU OCR 可选、GPU 脚本随包保留。`tools/build_release_directory.ps1` 会生成干净目录，`tools/build_installer.ps1` 在 Inno Setup 可用时完成编译。
2. 第一版安装到当前用户 `%LOCALAPPDATA%\Programs\NIKKE C ARENA Tool`，避免 Program Files 写入失败；配置、名单、截图与自定义底图通过 `onlyifdoesntexist` / `uninsneveruninstall` 保留。后续可再评估独立用户数据根目录。
3. 在不带 Python、不带 `.paddleocr` 缓存的干净 Windows 测试机上验收完整 OCR 回归和真实安装/升级/卸载流程。
4. 复核 PaddlePaddle、PaddleOCR、OpenCV、LibreHardwareMonitor、NVIDIA GPU 依赖等第三方许可证与 NOTICE 要求。
5. 设置发布配置默认值，并避免把开发机的 GPU/性能优先偏好带入正式包。
6. 评估代码签名与 SmartScreen 体验；不能通过隐藏 PowerShell 窗口来掩盖安全提示。

## 10. 最小验收矩阵

| 场景 | 预期 |
| --- | --- |
| 干净 Windows，无外部 Python、未选 CPU OCR、已安装 runtime_core | GUI 能启动；截图/拼图可用；OCR 明确提示未安装 |
| 干净 Windows，安装 CPU OCR，断网且无用户 `.paddleocr` | GUI 与单图/四图 OCR 都能运行 |
| CPU OCR，1920/2560/3440/3840 样图 | 战力、名称、收藏品、循环等级、胜负均正常导出 |
| 有 NVIDIA GPU，用户运行 GPU 配置脚本 | GPU 模式可选，CUDA 识别正常 |
| 无 NVIDIA GPU 或 GPU 配置失败 | CPU 模式仍可用，GUI 不崩溃 |
| 安全热保护模式 | 控制文件、进度、暂停/终止和 block 间歇正常 |
| 自动截图流程 | 不受 OCR 温控/暂停逻辑干预 |
| 名单编辑 | 写入本地 JSON 和 backup；无联网名单下载 |
| 输出检查 | `ArenaData`、`参赛阵容`、`_result.json`、`_roster.json` 字段符合第 6.4 节 |

## 11. 当前代码状态与工作区提示

Git 根目录：`outputs/.git`，当前基线提交：`2150d64 Initial project snapshot`。

交接时工作区包含近期 OCR 改动：

```text
M dataanalysis/arena_ocr_tool/main.py
M dataanalysis/arena_ocr_tool/recognizer/arena_ocr.py
M dataanalysis/arena_ocr_tool/recognizer/exporter.py
M dataanalysis/arena_ocr_tool/recognizer/result_parser.py
M nikke_round_config.json                 （用户本机配置，不要随意覆盖）
M nikke_gui_launcher.ps1
M run_stitcher.bat
M run_character_capture.bat
M run_all_characters.bat
M dataanalysis/arena_ocr_tool/requirements-ocr.txt
?? dataanalysis/arena_ocr_tool/requirements-ocr-cpu.lock.txt
?? dataanalysis/arena_ocr_tool/models/paddle_default/
?? tools/build_portable_runtimes.ps1
?? dataanalysis/arena_ocr_tool/backups/
?? dataanalysis/arena_ocr_tool/tmp/
?? dataanalysis/arena_ocr_tool/tools/evaluate_power_cv.py
```

封装前应先由负责方审阅、测试并提交需要进入发布版本的源码；开发评估输出、备份和样图不应自动进入普通发布包。

## 12. 建议先读的资料

```text
PACKAGE_MANIFEST_20260704.md
tools/build_portable_runtimes.ps1
tools/build_release_directory.ps1
tools/verify_release_directory.ps1
tools/build_installer.ps1
installer/NIKKE_Arena_Tool.iss
GPU_OCR_RUNTIME_SETUP_GUIDE.md
OCR_PERFORMANCE_THERMAL_PROTECTION_PLAN_20260703.md
PROJECT_HANDOFF_20260701.md
OCR_HANDOFF_20260701.md
dataanalysis/arena_ocr_tool/backups/POWER_OCR_ATTEMPTS_20260708.md
```

读取后再动封装代码。先建立一份干净发布目录并完成最小验收矩阵，确认路线可行后再考虑瘦身、安装器美化或 EXE 化。
