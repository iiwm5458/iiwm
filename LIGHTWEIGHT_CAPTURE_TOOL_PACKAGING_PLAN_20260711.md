# NIKKE C ARENA 轻量化纯截图工具封装方案

状态：待确认。本文只定义轻量版的 GUI、运行边界与封装方案，不执行代码修改或安装包构建。

## 1. 目标

制作一个与完整版独立安装的“轻量化纯截图工具”：

- 保留单人、应援、晋级赛与 TOP8 自动化截图、赛果页截图、拼图、自定义底图、输出命名与参数保存。
- 不携带 PaddleCPU、PaddleGPU、PaddleOCR、OpenCV OCR 依赖、OCR 模型或 GPU 配置脚本。
- 不要求用户安装 Python；仅携带截图与拼图所需的私有 runtime_core。
- 保留 OCR 相关入口的可见性，但点击后只提示完整版要求，不执行识别、文件选择、数据导出或名单编辑。

建议产品名：

~~~
NIKKE C ARENA 截图工具 轻量版
~~~

建议安装包名：

~~~
NIKKE_Arena_Capture_Lite_Setup_<版本号>.exe
~~~

## 2. 独立 GUI 方案

不直接删改完整版 GUI。新增独立入口与独立界面脚本：

~~~
run_capture_lite.bat
nikke_capture_lite_launcher.ps1
~~~

轻量版 GUI 基于现有主界面视觉风格重新裁剪，保留：

1. C ARENA 单人阵容截图。
2. 应援双方阵容截图。
3. C ARENA 晋级赛截图。
4. C ARENA TOP8 冠军争霸赛截图。
5. 打开截图文件夹。
6. 截图与图像识别参数设置中的截图等待时间、详细战果加载等待时间、底图选择与主题切换。
7. 左下角站点超链接、程序图标、全屏截图提醒、Alt + 2 紧急停止。

轻量版主界面保留“战斗图像识别”入口；点击后可进入完整的战斗图像识别二级页，作为完整版 OCR 能力的展示。该页面不启动 OCR 进度窗口或导出 JSON/Excel 工作流。

“C ARENA 当前赛季全部战斗图像一键截图”在轻量版主界面中隐藏，不提供二级页面或执行入口。

## 3. OCR 入口处理

### 3.1 统一提示文案

所有 OCR 相关入口统一使用：

~~~
该功能依赖 PaddleCPU/PaddleGPU 图像识别环境，请指挥官安装完整版工具。
~~~

提示仅有“确认”按钮，关闭提示后留在当前页面，不启动 OCR 子进程，不尝试寻找系统 Python，也不访问任何网络。

### 3.2 按钮映射

| 现有入口 | 轻量版处理 |
| --- | --- |
| 主面板“战斗图像识别” | 保留按钮与视觉位置；点击正常进入战斗图像识别二级展示页。 |
| 战斗图像识别页的选择图像、示例图、四个卡槽、四个清除按钮 | 保留视觉与可点击状态；点击显示统一提示，不弹出文件选择框、不改变卡槽状态。 |
| 战斗图像识别页的执行识别、打开数据文件夹 | 保留视觉与可点击状态；点击显示统一提示，不启动识别、不创建数据文件夹。 |
| “更新妮姬名单” | 保留为 OCR 相关入口时，点击显示统一提示；不打开名单管理器。 |
| 赛季一键截图页中的 OCR/导出相关说明或控制 | 删除，不展示。 |
| 主面板“C ARENA 当前赛季全部战斗图像一键截图” | 隐藏；轻量版不提供全赛季一键截图。 |
| CPU/GPU OCR 运行模式 | 在参数页保留灰色不可选控件，仅用于说明完整版提供该能力。 |
| GPU 环境配置教程 PDF 超链接 | 删除。 |
| GPU 配置脚本与 PDF/Markdown 教程 | 不封装。 |

战斗图像识别展示页顶部增加醒目说明：

~~~
以下为完整版战斗图像识别功能展示。轻量版仅提供自动化截图与拼图；如需识别、导出与名单校准，请安装完整版工具。
~~~

说明：“更新妮姬名单”本身不直接调用 Paddle，但它只服务于 OCR 名称校准；轻量版将其视作 OCR 相关入口，避免用户编辑一个不会被使用的数据文件。

## 4. 参数设置页

轻量版参数页保留截图参数：

- 普通点击等待时间。
- 黑色按钮的详细战果加载等待时间。
- 当前主题、底图选择、用户参数持久化。

OCR 区域改为只读灰色状态：

- CPU 选项：灰色、不可点击。
- GPU 选项：灰色、不可点击。
- OCR 温度保护、性能说明、GPU 可用状态、GPU 教程链接：删除。
- OCR 运行模式的说明改为“图像识别功能仅在完整版工具中提供”。

这样不会误导用户安装后可以使用 OCR，也不会出现无效的 GPU 配置入口。

## 5. 自动截图边界

轻量版保留的自动化截图不依赖 PaddleCPU/PaddleGPU：

| 自动化行为 | 轻量版方案 |
| --- | --- |
| 单人、应援、GROUP、TOP8 截图与拼图 | 原样保留。 |
| 16 强、32 强战果页标签判断 | 保留蓝色像素探测逻辑。 |
| 16 强正确战果按钮选择 | 保留紫色像素探测逻辑。 |
| 冠亚军正确战果按钮选择 | 保留粉色像素探测逻辑。 |
| 赛果胜方判断 | 保留青色高亮像素判断逻辑。 |
| 全赛季一键截图 | 不提供入口，不执行。 |
| 全赛季昵称 OCR 交叉核对、对阵纠偏 | 不提供。 |

实现要求：轻量版 GUI 不向截图 worker 传入全赛季一键截图参数。轻量包不携带 OCR 模块，普通截图流程也不得尝试加载、搜索或导入任何 OCR 模块。

## 6. 轻量版目录

建议发布目录：

~~~
NIKKE_C_ARENA_Capture_Lite/
  run_capture_lite.bat
  nikke_capture_lite_launcher.ps1
  nikke_round_stitcher.py
  nikke_character_capture.py
  nikke_round_config.json
  nikke_character_capture_config.json
  assets/
  runtime_core/
  screenshots/
  custom_backgrounds/
  support_custom_backgrounds/
  group_custom_backgrounds/
~~~

必须保留：

- runtime_core：Python 3.10 与 Pillow，供截图、屏幕抓取和拼图使用。
- assets：背景、图标、空卡槽素材、示例图、站点图标和程序图标。
- group_custom_backgrounds\pixiewall-a1cg6q-3840x2160.jpg：当前随完整版分发的自定义 GROUP/赛季背景。
- 三个用户可写背景目录与 screenshots 目录。

不得封装：

~~~
runtime_cpu/
runtime_python310_base/
runtime_gpu/
wheelhouse_gpu/
dataanalysis/arena_ocr_tool/
vendor/LibreHardwareMonitorLib/
setup_gpu_runtime.bat
setup_gpu_runtime_cn.bat
setup_gpu_runtime.ps1
GPU_OCR_RUNTIME_SETUP_GUIDE.md
GPU_OCR_RUNTIME_SETUP_GUIDE.pdf
~~~

## 7. 安装器设计

新增独立 Inno Setup 脚本：

~~~
installer/NIKKE_Arena_Capture_Lite.iss
~~~

规则：

- 使用独立 AppId，不能覆盖或卸载完整版。
- 默认目录使用独立名称，例如：

~~~
%LOCALAPPDATA%\Programs\NIKKE C ARENA 截图工具 轻量版
~~~

- 安装目录与开始菜单创建轻量版快捷方式。
- 可选创建桌面快捷方式。
- 使用现有程序图标；安装器图标仍使用现有安装器图标。
- 不提供组件选择页。
- 用户截图、用户参数与自定义底图目录使用保留策略，卸载时不删除。

新增构建脚本：

~~~
tools/build_capture_lite_release.ps1
tools/verify_capture_lite_release.ps1
tools/build_capture_lite_installer.ps1
~~~

完整版构建脚本、完整版安装器与完整版 GUI 均保持独立，不被轻量版改动影响。

## 8. 轻量化 GUI 验收

1. 没有系统 Python、没有 Paddle、没有 runtime_cpu 的干净 Windows 环境中，轻量版可启动。
2. 主界面的所有截图入口可进入二级页面并正常执行截图。
3. GROUP、TOP8 截图与拼图输出不加载 PaddleOCR。
4. 16 强、32 强、4 强、冠亚军的战果页按钮选择仍由颜色逻辑正确完成。
5. 主界面不显示“C ARENA 当前赛季全部战斗图像一键截图”。
6. 点击“战斗图像识别”可进入完整的二级展示页；所有选图、卡槽、清除、示例、执行识别和数据文件夹按钮均显示统一提示，且不会创建 OCR 日志、OCR 输出或 Python OCR 子进程。
7. 点击“更新妮姬名单”显示统一提示，且不会打开名单管理器。
8. CPU/GPU OCR 控件为灰色不可用；没有 GPU PDF 超链接。
9. 点击参数保存后，截图延迟与主题设置在下次启动时保留。
10. 安装目录不含 runtime_cpu、runtime_python310_base、dataanalysis、GPU 脚本和 GPU 教程 PDF。
11. 完整版与轻量版可同时安装、分别启动、分别卸载，互不覆盖。

## 9. 预期体积

轻量版主要由 assets 与 runtime_core 构成：

- runtime_core：约 31 MB。
- assets：约 50 至 60 MB。
- 截图脚本、GUI、配置与安装器逻辑：体积很小。

预计安装后目录约 90 至 120 MB；最终安装包大小以实际 Inno Setup 压缩结果为准，预计显著小于完整版。

## 10. 确认后实施顺序

1. 新建轻量版专用 GUI 与入口脚本；隐藏全赛季一键截图入口。
2. 将 OCR 相关入口替换为统一提示，参数页 OCR 控件灰化并移除 GPU PDF 链接。
3. 新建轻量版发布目录构建、验证和 Inno Setup 安装器脚本。
4. 在无系统 Python、无 Paddle 的环境假设下进行静态运行时验证。
5. 编译轻量版安装包，核验安装包文件清单、体积、哈希及与完整版并存安装行为。

## 11. 首次构建记录

首次轻量版安装包已于 2026-07-11 构建完成：

~~~
dist/installer/NIKKE_Arena_Capture_Lite_Setup_0.1.0.exe
~~~

构建后的静默安装冒烟测试已通过：安装目录中的 `runtime_core` 可以导入 Pillow 并执行截图 worker 的帮助命令，轻量版 GUI 的自检通过；同时确认安装目录不含 `runtime_cpu`、`runtime_python310_base`、`runtime_gpu`、`dataanalysis`、GPU 配置脚本或 GPU 教程 PDF。

安装包大小为 48,210,751 字节，SHA-256 为：

~~~
56D7D75BB3274CFB6C750B389DC9EED152AD6B0693225D6838CE91C15BCE9258
~~~
