# NIKKE 工具封装清单目录（内置 Python/OCR runtime）

生成时间：2026-07-04

目标：制作一个可在用户电脑上直接运行的正式包。正式包内置 Python/OCR runtime，不依赖 Codex 缓存路径，不要求用户自行安装 PaddleOCR 才能使用基础功能。

## 一、正式包根目录建议

建议最终封装目录命名为：

```text
NIKKE_Arena_Tool/
```

建议目录结构：

```text
NIKKE_Arena_Tool/
  run_gui.bat
  setup_gpu_runtime.bat
  setup_gpu_runtime_cn.bat
  setup_gpu_runtime.ps1
  nikke_gui_launcher.ps1
  nikke_round_stitcher.py
  nikke_character_capture.py
  nikke_round_config.json
  nikke_character_capture_config.json

  assets/
  dataanalysis/
    arena_ocr_tool/
  vendor/
    LibreHardwareMonitorLib/

  runtime_core/
  runtime_cpu/

  screenshots/                  空目录，运行后自动输出
  custom_backgrounds/           空目录
  support_custom_backgrounds/   空目录
  group_custom_backgrounds/     空目录

  docs/
    README_自动截图拼图.md
    README_角色详情自动截图.md
    GPU_OCR_RUNTIME_SETUP_GUIDE.md
    OCR_HANDOFF_20260701.md     可选，开发交接用
```

## 二、必须包含

### 入口与主逻辑

```text
run_gui.bat
nikke_gui_launcher.ps1
nikke_round_stitcher.py
nikke_character_capture.py
nikke_round_config.json
nikke_character_capture_config.json
```

说明：

- `run_gui.bat` 是用户入口。
- `nikke_gui_launcher.ps1` 是 GUI 主程序。
- `nikke_round_stitcher.py` 是 C ARENA 自动截图、拼图、赛季一键截图核心。
- `nikke_character_capture.py` 是角色详情截图逻辑，当前不是主流程，但建议保留。
- 两个 JSON 配置文件必须随包携带。

### GUI 与截图资源

```text
assets/
```

当前 `assets` 约 53MB，已检查关键资源存在。建议完整保留，避免遗漏背景、按钮、图标、卡槽贴图、示例图。

### OCR 工具核心

```text
dataanalysis/arena_ocr_tool/
```

当前约 94MB。建议保留：

```text
dataanalysis/arena_ocr_tool/main.py
dataanalysis/arena_ocr_tool/recognizer/
dataanalysis/arena_ocr_tool/data/
dataanalysis/arena_ocr_tool/models/
dataanalysis/arena_ocr_tool/requirements-ocr.txt
dataanalysis/arena_ocr_tool/requirements-ocr-cpu.lock.txt
dataanalysis/arena_ocr_tool/requirements-ocr-gpu.txt
dataanalysis/arena_ocr_tool/install_ocr_dependencies.ps1
```

建议删除：

```text
dataanalysis/arena_ocr_tool/__pycache__/
```

### 温控/硬件监测依赖

```text
vendor/LibreHardwareMonitorLib/HidSharp.dll
vendor/LibreHardwareMonitorLib/LibreHardwareMonitorLib.dll
```

已检查存在。建议保留。

### 内置 runtime

正式包需要内置两个互不依赖的可搬运 Python runtime：

```text
runtime_core/
  python.exe

runtime_cpu/
  python.exe
```

用途：

- `runtime_core`：自动截图与拼图，包含 Python 3.10.8 和 Pillow。
- `runtime_cpu`：CPU OCR，包含 Python 3.10.8、PaddleOCR、Paddle、OpenCV、openpyxl 等依赖。
- 两个 runtime 都是 CPython embeddable 目录，不是 `venv`，不会指向开发机 Python。

当前状态：

- `runtime_core/python.exe` 已创建，约 31 MB，截图 worker 已验证。
- `runtime_cpu/python.exe` 已创建，约 974 MB，CPU OCR 依赖已验证。
- 默认 PaddleOCR 模型已放入 `dataanalysis/arena_ocr_tool/models/paddle_default/`，约 21 MB。

当前已有但普通正式包建议不内置：

```text
runtime_gpu/
  Scripts/python.exe
```

当前 `runtime_gpu` 存在，约 4.3GB。它用于本机开发和测试 GPU OCR。

为了避免直接再分发 NVIDIA CUDA/cuDNN runtime 带来的许可风险，普通正式包建议不包含 `runtime_gpu`，而是保留 `setup_gpu_runtime.bat` / `setup_gpu_runtime.ps1`，让用户自行从 PyPI 配置 GPU 环境。

## 三、建议排除

### 大量历史截图

```text
screenshots/
```

当前约 10.6GB。正式包建议只保留空目录：

```text
screenshots/.keep
```

### OCR 调试输出与标注数据

建议排除：

```text
dataanalysis/manual_annotations/
dataanalysis/ocr_output/
dataanalysis/ocr_output_region_fixed/
dataanalysis/ocr_output_region_test/
dataanalysis/ocr_output_region_test2/
dataanalysis/ocr_output_slot_fixed/
dataanalysis/ocr_output_slot_fixed2/
dataanalysis/ocr_runtime_test/
dataanalysis/1920_name_diff_crops/
dataanalysis/1920_power_diff_crops/
dataanalysis/1920_remaining_name_errors/
dataanalysis/gpt指令优化/
```

这些目录当前合计超过 1GB，主要是开发/调试产物。

### 巨型测试样图

可选排除：

```text
dataanalysis/64强-我要所有人（GROUP）的数据.png   约 194MB
dataanalysis/ocr_region_plan_debug.png
dataanalysis/例图1.png
```

如果程序默认 OCR 单图示例仍需要 `例图1.png`，则保留；否则建议移入 docs/examples 或排除。

### 根目录开发验证图

建议排除：

```text
attrs_var_*.png
character_*_check*.png
collect_*.png
entries_*.png
equip_*.png
fixed_*_check.png
layout_preview_new_logic.png
nikke_stitched_*.png
preview_regions.png
skill_*.png
```

这些多为开发验证图，不属于正式运行必需文件。

### 构建/离线安装缓存

```text
wheelhouse_gpu/
```

当前约 1.12GB。

取舍：

- 普通正式包不带 `runtime_gpu`，也不带 `wheelhouse_gpu`。
- 用户如需 GPU 模式，通过 `setup_gpu_runtime.bat` 自行从 PyPI 配置。
- `wheelhouse_gpu` 仅保留在开发包或个人自用环境，不进入普通发布包。

### 开发交接文档

建议不放普通用户包，放开发包：

```text
README_新对话交接_20260701.md
PROJECT_HANDOFF_20260701.md
SEASON_CAPTURE_DESIGN.md
OCR_PERFORMANCE_THERMAL_PROTECTION_PLAN_20260703.md
```

## 四、当前必须修正的问题

### 1. 移除 Codex 缓存 Python 绝对路径

当前状态：

```text
nikke_gui_launcher.ps1
run_character_capture.bat
run_stitcher.bat
run_all_characters.bat
```

已改为相对路径优先：

```text
runtime_core\python.exe
```

建议解析顺序：

```text
1. runtime_core\python.exe（截图/拼图）
2. runtime_cpu\python.exe（CPU OCR；截图 fallback）
3. runtime_gpu\Scripts\python.exe（仅 OCR GPU）
4. %LOCALAPPDATA%\Programs\Python\Python312\python.exe
5. PATH 中的 python.exe
```

### 2. 可搬运 runtime 已创建

当前检查：

```text
runtime_core\python.exe: 存在，sys.prefix == sys.base_prefix
runtime_cpu\python.exe: 存在，sys.prefix == sys.base_prefix
Python: 3.10.8
Paddle: 2.6.2
默认模型：项目内显式路径加载，空用户 HOME 下不会创建 .paddleocr
```

已安装并验证：

```text
Pillow
paddlepaddle==2.6.2
paddleocr==2.7.3
numpy==1.26.4
rapidfuzz
opencv-python-headless==4.9.0.80
lxml
openpyxl
```

`requirements-ocr.txt` 已补入 `openpyxl` 与 `Pillow`。

### 3. worker exe 当前不存在

当前检查：

```text
nikke_round_stitcher_worker.exe: 不存在
nikke_character_capture_worker.exe: 不存在
```

如果内置 Python runtime，可以不打 worker exe；`run_stitcher.bat` / `run_character_capture.bat` 现已优先使用随包 `runtime_core`，并在其缺失时回退到 `runtime_cpu`。

如果要减少用户侧 Python 可见性，也可以后续再打 worker exe。

### 4. 历史 manifest / 模板数据含绝对路径

扫描发现历史 manifest 与模板评估文件中有：

```text
C:\Users\iiwm\Documents\Codex\...
```

这些多在历史截图、collection CV 模板评估输出中。普通用户包建议排除这些历史输出；如果某些模板运行时必须读取，需要改成相对路径。

## 五、建议封装前操作顺序

1. 新建干净目录：

```text
NIKKE_Arena_Tool/
```

2. 复制必须包含文件和目录。

3. 使用 `tools/build_portable_runtimes.ps1 -ReplaceExisting` 构建 `runtime_core`、`runtime_cpu` 与默认 PaddleOCR 模型。

4. 普通正式包不保留 `runtime_gpu`：

- 降低包体。
- 避免直接再分发 NVIDIA CUDA/cuDNN runtime。
- 保留 `setup_gpu_runtime.bat` / `setup_gpu_runtime.ps1`，让用户自行在线配置 GPU 环境。

5. 修改脚本和 bat 的 Python 搜索顺序，移除 Codex 缓存路径。

6. 清理 `screenshots`、OCR 调试目录和根目录测试图片。

7. 在干净目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\nikke_gui_launcher.ps1 -Check
```

8. 测试：

```text
GUI 启动
单人阵容截图
GROUP 截图
TOP8 截图
当前赛季一键截图
单图 OCR
四卡槽 OCR
打开数据文件夹
打开日志
CPU/GPU 模式切换
过热保护/性能优先切换
```

## 六、建议最终包类型

### 普通用户包

包含：

```text
runtime_core
runtime_cpu
assets
dataanalysis/arena_ocr_tool
vendor
setup_gpu_runtime.bat
setup_gpu_runtime_cn.bat
setup_gpu_runtime.ps1
核心脚本与配置
空输出目录
简短 README
```

排除：

```text
screenshots 历史数据
manual_annotations
ocr_output*
runtime_gpu
wheelhouse_gpu
根目录测试 PNG
开发交接文档
```

### 开发完整包

包含普通用户包之外，再加：

```text
runtime_gpu
wheelhouse_gpu
manual_annotations
OCR 评估/调试目录
交接文档
测试样图
```

## 七、当前验证结果

已通过：

```text
nikke_gui_launcher.ps1 -Check
nikke_round_stitcher.py 语法编译
nikke_character_capture.py 语法编译
dataanalysis/arena_ocr_tool/main.py 语法编译
```

当前资源检查：

```text
assets：关键资源存在，约 53MB
dataanalysis/arena_ocr_tool：约 94MB
runtime_gpu：存在，约 4.3GB
runtime_core：约 31 MB，可离线运行截图 worker
runtime_cpu：约 974 MB，可离线导入 CPU OCR；不依赖开发机 Python
默认 PaddleOCR 模型：约 21 MB，空 HOME 初始化主 reader 与日/韩昵称 reader 已验证
vendor/LibreHardwareMonitorLib：存在
```
