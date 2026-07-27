# NIKKE C ARENA Tool 项目交接文档（2026-07-15）

> **用途：** 供新的 Codex 对话或后续开发者直接接手当前项目。本文反映截至 2026-07-15 17:11（UTC+8）的真实代码、发行物与补丁状态。请优先以本文为准；旧交接文档仅作历史参考。

## 0. 阅读顺序与根目录

建议顺序：

1. 本文：当前版本、风险边界、近期修复、下一步。
2. `README.md`：项目概览与授权说明。
3. `PROJECT_DEVELOPER_HANDOFF_20260711.md`：Git、可搬运 runtime、安装器与发布原则。
4. `OCR_HANDOFF_20260701.md`：OCR 历史性能问题与导出目标。其“不改自动截图 OCR 链路”的边界仍有效，部分性能结论已经过时。
5. `PACKAGING_HANDOFF_20260710.md`：封装设计背景。Windows PowerShell 控制台可能显示乱码，请用 UTF-8 编辑器打开。

项目根目录：

~~~text
C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs
~~~

下文的“根目录”均指该路径。

## 1. 当前产品和发行物

项目有两个独立产品，**不可互相覆盖安装，也不可用其中一个的目录替代另一个。**

| 产品 | 启动入口 | 包含能力 | 明确不包含 |
| --- | --- | --- | --- |
| 完整版 `NIKKE C ARENA Tool` | `run_gui.bat` | 自动截图、拼图、图像工具、CPU OCR、可选 GPU OCR、Excel/JSON 导出、妮姬名单维护 | GPU runtime 不随安装包分发 |
| 轻量版 `NIKKE C ARENA 截图工具 轻量版` | `run_capture_lite.bat` | 自动截图、拼图、图像工具、赛果判定、参数保存 | PaddleCPU/PaddleGPU、OCR 导出、名单维护、赛季全部战斗图像一键截图 |

### 当前正式版本

| 产品 | 版本 | 发行目录 | 安装包 |
| --- | --- | --- | --- |
| 完整版 | `0.1.13` | `dist\r_0.1.13` | `dist\installer\NIKKE_Arena_Tool_Setup_0.1.13.exe` |
| 轻量版 | `0.1.5` | `dist\lite_r_0.1.5` | `dist\installer\NIKKE_Arena_Capture_Lite_Setup_0.1.5.exe` |

对应 `RELEASE_INFO.json` 构建时间：

- 完整版：2026-07-15 14:43:42 +08:00。
- 轻量版：2026-07-15 14:49:16 +08:00。

### 当前升级补丁

`dist\updates` 中现有：

~~~text
NIKKE_C_ARENA_Tool_完整版_升级补丁_0.1.13.zip
NIKKE_C_ARENA_Capture_Lite_轻量版_升级补丁_0.1.5.zip
更新日志_2026-07-15.txt
~~~

补丁最后重建时间为 2026-07-15 17:11:35。历史对比基线是：

- 完整版：`0.1.11`。不要以曾被误提前构建的 `0.1.12` 当作用户版本或补丁基线。
- 轻量版：`0.1.4`。

`0.1.12` 仅保留在 `dist` 供追溯，不再作为正式发布参考。

## 2. 当前工作树：绝不能随意还原

项目已建立本地 Git，但工作树是脏的，含正常的源码变更、未跟踪文件、以及若干**有意删除**的图片资源。接手第一步可以运行 `git status --short`，但不得因为出现 `D` 就执行 `git restore`、`git checkout --` 或批量恢复。

特别是下列背景和站点图片，以及 `group_custom_backgrounds\pixiewall-a1cg6q-3840x2160.jpg` 的删除，是项目方为规避素材版权风险而做出的决定。用户已经明确说明“故意删除”，**不得恢复、不得重新封装，也不要为了清理 Git 状态将它们加回去。**

不要提交到公开 Git 仓库、也不要随意纳入发布包：

~~~text
runtime_core\
runtime_cpu\
runtime_gpu\
runtime_python310_base\
wheelhouse_gpu\
work\
dist\
screenshots\
custom_backgrounds\
support_custom_backgrounds\
dataanalysis\arena_ocr_tool\tmp\
dataanalysis\arena_ocr_tool\backups\
~~~

编码规则：

- Windows PowerShell 5.1 下，包含中文的 `.ps1` 必须保存为 **UTF-8 with BOM**。
- Python 源码使用 UTF-8。
- 不要再用 PowerShell 的通用 `ConvertTo-Json` 深合并用户配置，详见第 9 节。

## 3. 架构与关键文件

~~~text
完整版
run_gui.bat
  -> nikke_gui_bootstrap.ps1
  -> nikke_gui_launcher.ps1（WPF GUI）
  -> runtime_core\python.exe（截图、拼图、图像工具）
  -> runtime_cpu\python.exe（CPU OCR）
  -> runtime_python310_base\python.exe + 用户配置的 GPU 依赖（可选 GPU OCR）

轻量版
run_capture_lite.bat
  -> nikke_capture_lite_launcher.ps1（独立 WPF GUI）
  -> runtime_core\python.exe（截图、拼图、图像工具）
~~~

| 职责 | 文件 |
| --- | --- |
| 完整版 WPF GUI、OCR 启动和设置保存 | `nikke_gui_launcher.ps1` |
| 完整版启动 bootstrap | `nikke_gui_bootstrap.ps1` |
| 轻量版 WPF GUI | `nikke_capture_lite_launcher.ps1` |
| 自动鼠标操作、截图、裁切、拼图、截图流程 OCR | `nikke_round_stitcher.py` |
| 角色详情自动截图 | `nikke_character_capture.py` |
| JPEG 压缩和通用拼图 | `nikke_image_tools.py` |
| 截图坐标、裁切、等待时间、用户保存参数 | `nikke_round_config.json` |
| 战斗图 OCR CLI | `dataanalysis\arena_ocr_tool\main.py` |
| OCR 解析与纠错 | `dataanalysis\arena_ocr_tool\recognizer\result_parser.py` |
| Excel/JSON 导出 | `dataanalysis\arena_ocr_tool\recognizer\exporter.py` |
| 妮姬名称/别名 | `dataanalysis\arena_ocr_tool\data\nikke_names.json` |
| 完整版发行目录/安装器 | `tools\build_release_directory.ps1`、`tools\build_installer.ps1` |
| 轻量版发行目录/安装器 | `tools\build_capture_lite_release.ps1`、`tools\build_capture_lite_installer.ps1` |
| 更新补丁 | `tools\build_update_patches.ps1` |

自动截图只通过外部桌面鼠标/键盘输入和屏幕截图工作。**不得读取、修改、注入游戏客户端内存，不得处理游戏客户端文件。** 这是安全和封号风险边界。

## 4. Runtime、CPU OCR 和 GPU OCR

### 4.1 Runtime 分工

| 目录 | 用途 | 分发范围 |
| --- | --- | --- |
| `runtime_core` | CPython 3.10 embeddable + Pillow 等截图/拼图依赖 | 完整版与轻量版 |
| `runtime_cpu` | PaddleOCR、CPU OCR 依赖、默认离线模型 | 仅完整版 |
| `runtime_python310_base` | GPU 一键配置使用的干净 Python 3.10 基础环境 | 仅完整版 |

这些 runtime 可独立复制运行，不应依赖 Codex 缓存路径或用户系统 Python。`runtime_core` 是自动截图和拼图的依赖，因此纯截图工具可以在没有 PaddleCPU/GPU 的情况下工作。

当前完整安装包按用户决定固定为“带 CPU OCR 的完整体”，不再让用户选择是否安装 CPU OCR；纯截图需求由独立轻量版满足。

### 4.2 GPU 策略与许可

GPU runtime 不随安装包分发，避免 CUDA/cuDNN/NVIDIA runtime 的再分发许可问题。完整版提供用户自行同意许可的一键配置：

~~~text
setup_gpu_runtime.bat
setup_gpu_runtime_cn.bat
setup_gpu_runtime_aliyun.bat
setup_gpu_runtime.ps1
GPU_OCR_RUNTIME_SETUP_GUIDE.md
GPU_OCR_RUNTIME_SETUP_GUIDE.pdf
~~~

这些脚本锁定依赖版本，并使用工具自带 `runtime_python310_base`，不会修改或破坏用户系统 Python。GPU 模式只有检测到环境可用时才允许在 GUI 选择，否则保持灰色。

清华镜像曾有用户报错，已添加阿里云镜像 BAT 作为中国大陆网络备选。将来改 GPU 依赖版本，必须一起更新四个脚本、MD、PDF、发行物、补丁。

### 4.3 OCR 功能边界

完整版必须保留：

- 单图识别：后续还会迁移给其他按钮。
- 四卡槽赛季识别：按文件名而非卡槽顺序归类，顺序是 `64进32全部`、`32进16全部`、`16进8全部`、`TOP8-决赛`。
- `64进32全部` 读取晋级赛所有 Group 的 8 进 4 详细赛果，生成 64 名玩家昵称、ID、P1-P5 和战力，输出到 Excel Sheet2。
- 后续三张图主要识别昵称、ID、胜负，以 ID 为主和 Sheet2 交叉验证，再回填阵容/战力。
- Excel/JSON、进度、错误日志、打开数据文件夹均属于完整版。

**不要为了手工上传 OCR 的性能或导出逻辑，修改自动截图内的 OCR 配对和拼图链路。** 下列 `nikke_round_stitcher.py` 函数是自动截图正确匹配的关键：

~~~text
get_season_ocr
recognize_profile_aliases
result_name_candidates_from_screen
collect_cached_stage_results
run_season_capture
stitch_cached_stage
~~~

### 4.4 OCR 最近修复

`main.py` 和 `result_parser.py` 最新修改包含：

- OCR 图像解析支持 `2560x1600`，并支持 `--force-detailed-results`。
- 循环等级/反常等级支持 `1..999`。
- 合并文本框、数值行的二次确认。
- 常见尾部字形修复：`66->99`、`266->299`、`366->399`、`666->999`。
- 名单新增 `灰姑娘：琉璃波光`、`玛律恰那：海洋进修`，匹配器启动时会从特殊名安全派生别名。

这些改动已进入完整版 `0.1.13` 与其补丁；轻量版不含 OCR runtime 和导出。

## 5. GUI 当前状态

### 5.1 两个版本共有的部分

- 两种主题；粉色主题使用用户提供的图，图片来源文字为 `GPT 5.6Sol`。
- 用户参数保存在 `nikke_round_config.json`，下次启动必须继续沿用。
- 任务栏图标通过 `AppUserModelId`、`WM_SETICON`/`Set-WindowTaskbarIcon` 设置为 `assets\app_doro_commander.ico`；快捷方式也应使用同一个 ICO。
- 主窗口左下角原有过多的超链接图标已删除。
- 图像工具：四卡槽、PNG/JPG 选择、PNG 压缩为 JPEG、横向/纵向拼接与像素间距。处理窗口无系统标题条，完成提示使用主题化窗口并带“指挥官，”称呼。
- 卡槽只允许 PNG/JPG，初始目录应为截图输出目录，四槽不得选同名文件。

### 5.2 完整版特有部分

- `战斗图像识别` 页面有四卡槽、单图逻辑、按文件名就绪状态、OCR 进度窗口和日志。
- OCR 运行时禁用本程序其他截图与识别操作；OCR 窗口在本程序前层、但不抢占其他软件。
- OCR 日志使用 UTF-8 BOM，窗口实时显示；异常时可打开日志。
- 成功时标题改为“任务完成，指挥官”，隐藏等待文案，显示“打开数据文件夹”。
- OCR 运行模式只保留 CPU/GPU；旧性能模式、内存模式、Paddle CPU 线程限制已停用/注释，不要重新加回限制。
- 参数页有 GPU 说明、GPU 教程 PDF 链接和全屏截图的高亮提示，两个主题都必须可读。

### 5.3 轻量版特有部分

- 必须保持独立 `nikke_capture_lite_launcher.ps1`，不能把 Paddle OCR 偷带回轻量版。
- 隐藏 `C ARENA当前赛季全部战斗图像一键截图`。
- `战斗图像识别` 页面依然可进入，作为完整版的 Demo；选图、卡槽、清除、执行、数据目录、名单更新等行为只弹出“该功能依赖 PaddleCPU/PaddleGPU 图像识别环境，请安装完整版工具”。
- 轻量版不得启动 OCR 子进程、创建 OCR 输出、访问网络、寻找系统 Python。
- OCR 模式控件为灰色，移除 GPU 教程 PDF 链接。

## 6. 自动截图：服务器差异与详细页轮询

### 6.1 服务器检测与输出名

启动器检测三种客户端并传入 `--server`：

| 服务器 | GUI 状态 | 文件后缀 |
| --- | --- | --- |
| 国服 | `国服Running` | `-国服` |
| 国际服 | `国际服Running` | `-国际服` |
| 港澳台服 | `港澳台服Running` | `-港澳台` |

所有截图类型的文件名均应追加相应后缀。

### 6.2 国服与国际服/港澳台服的区别

| 场景 | 国服 | 国际服/港澳台服 |
| --- | --- | --- |
| 关闭赛果/弹窗 | Esc | 点击左右侧无关空白区：`clicks.modal_dismiss_side_points` |
| 晋级赛转冠军争霸赛 | Esc | 点击左下蓝色“返回”按钮：`season_return_button_ratio`，不可点击右边首页 |
| 详细赛果裁切 | `group_detailed_result=[1380,289,681,873]` | `group_detailed_result_global_hmt=[1380,356,681,788]`，去掉蓝标题带和底部残留 |
| 研究/循环等级末格 | 保持原逻辑 | `research_cards_global_hmt` + `research_card_slot_width_global_hmt` 补足辅助型等级右边缘 |

国际服和港澳台服 Esc 被游戏屏蔽或未正确传入，而鼠标正常；所以这些修改只在外部桌面输入层完成，不接触游戏客户端内部。

### 6.3 详细战果页轮询

`wait_for_detailed_result_page()` 的当前规则：

1. 点击黑色详细战果按钮。
2. 每 `detail_page_poll_interval_seconds` 轮询当前画面（默认 `0.35s`）。
3. 连续两次判断为完整详细页后，再固定等 `0.5s`。
4. **重新截取当前屏幕，再裁切详细战果区域。** 不保留轮询帧，也不生成 OCR 版/观赏版两份文件。
5. 到 `detail_page_timeout_seconds`（默认 `60s`）仍未就绪，直接弹出“检测到当前无法正常进入战果页，请指挥官检查网络环境后重试。”；不要再次点黑色按钮。

该轮询用于所有勾选“赛后数据（详）”的自动截图流程。它仅对小区域进行截图/像素结构检测，约每秒 3 次，性能开销低，且不依赖 PaddleOCR，因此轻量版也可工作。

国际服/港澳台服的 `DISCONNECTED` 等详细页存在不同特征，已做区域兼容。之前第三个黑色按钮卡住的根因就是其详细页与国服完整页特征不一致。国服当前严格逻辑保持不变，但未来版本更新可能出现同类问题，届时先保存全屏图和 `screenshots\logs` 日志，再做服务器条件下的增量处理。

### 6.4 等待参数

`nikke_round_config.json` 的 `timing` 当前关键默认值：

| 键 | 用途 | 默认 |
| --- | --- | --- |
| `after_round_click_seconds` | 普通点击后等待 | `0.8s` |
| `after_avatar_click_seconds` | 点用户头像到截图用户信息页；已独立于普通点击 | `2.0s` |
| `after_group_result_click_seconds` | 在赛果窗口内切换阶段标签后等待 | `0.8s` |
| `after_bracket_result_click_seconds` | 从出线图点击标签，打开简化赛果窗口后等待；已独立 | `1.0s` |
| `after_group_detail_click_seconds` | 点黑色详细赛果按钮后的最小等待 | `0.7s` |
| `detail_page_timeout_seconds` | 详细页轮询最大时间 | `60s` |
| `detail_page_poll_interval_seconds` | 轮询间隔 | `0.35s` |
| `after_profile_close_seconds` | 关闭用户资料页后等待 | `0.4s` |
| `after_escape_seconds` | 国服 Esc 后等待 | `0.45s` |

GUI 中头像页等待、出线图简化赛果等待的范围都是 `0.45..5s`，两项都必须在完整/轻量版保存并传给 `nikke_round_stitcher.py`。参数页已因新增控件收紧并可滚动，不要再用固定高度塞控件导致底部不可见。

### 6.5 分辨率

- 基准为 `3440x1440`；点击主要按比例/统一缩放。
- `2560x1600` 的**OCR 图像**解析可以支持，但自动截图适配方案曾尝试后按用户要求撤销，不能宣称自动化流程已支持该分辨率。
- 新增分辨率必须逐一验证点击点、裁切、详细页轮询探针、国际/HMT 特殊裁切和最终拼图，且不得动国服基准排版。

## 7. 赛季截图与拼图约束

- 一键赛季截图的四张图是 OCR 标注区的排版基准。晋级赛 64/32/16 与冠军争霸赛未选底图模式必须向它对齐，**不能反过来改变一键截图的 block 间距**。
- 自动截图最后不再导出 manifest 图片，相关逻辑已删除。
- 相关赛季完整数据页面默认详细赛果，简化赛果旧导出项已删除。
- 一键截图会用 OCR 做昵称配对、赛果标签判断、拼图排序；不要把它误当成完全不依赖识别的纯截图库。
- 轻量版独立的截图路径只依赖 `runtime_core` 与轻量判断逻辑；不得把 PaddleCPU/GPU 变成其隐式硬依赖。

## 8. 封装与安装器

只有用户明确要求时才封装。典型命令：

~~~powershell
Set-Location 'C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs'

# 完整版
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build_installer.ps1 -Version <新版本>

# 轻量版
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build_capture_lite_installer.ps1 -Version <新版本>
~~~

构建发行目录后先验证：

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\verify_release_directory.ps1 -ReleaseRoot .\dist\r_<版本>
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\verify_capture_lite_release.ps1 -ReleaseRoot .\dist\lite_r_<版本>
~~~

需要 Inno Setup 6。构建脚本会在下列位置寻找 `ISCC.exe`：

~~~text
work\inno_setup\program\ISCC.exe
C:\Program Files (x86)\Inno Setup 6\ISCC.exe
C:\Program Files\Inno Setup 6\ISCC.exe
~~~

封装后的最低验证：

1. 安装至含中文/空格的非开发路径，如 `D:\AI\新建文件夹\NIKKE C ARENA Tool`。
2. 普通启动应提醒用户以管理员身份启动；不再以 UAC 强制运行。管理员启动时截图必须正常。
3. 截图完成和 Alt+2 停止后的确认弹窗不能让程序闪退。
4. 完整版 CPU OCR 能定位 `runtime_cpu`，不能搜索 Codex 缓存路径。
5. 轻量版不含 `runtime_cpu`/`runtime_python310_base`，OCR 页只弹完整版提示。
6. 快捷方式、安装目录快捷方式、任务栏图标应均使用正确 ICO。
7. 检查版权风险资源没有被重新封入安装包。

## 9. 升级补丁事故与当前方案

### 9.1 已出现的真实故障

用户打旧补丁后发生截图崩溃：

~~~text
ValueError: not enough values to unpack (expected 4, got 2)
get_research_card_rects -> crop_rects_from_image -> scale_rect
~~~

根因是旧补丁使用 PowerShell 通用 JSON 深合并和 `ConvertTo-Json`。Windows PowerShell 5.1 会把二维 JSON 数组重新序列化为对象，例如：

~~~json
{"value":[1500,724,132,112],"Count":4}
~~~

而 Python 期待的是 `[x, y, width, height]`，因此迭代该对象只得到两个键并异常。特别容易坏的是：

- `crops.research_cards_global_hmt`：二维四元组数组。
- `clicks.modal_dismiss_side_points`：二维坐标数组。
- 未来所有嵌套数组配置。

### 9.2 已修正的补丁方式

`tools\build_update_patches.ps1` 已改为：

1. 用户解压并运行 `apply_update.bat`。
2. 脚本验证所选目录包含正确启动 BAT。
3. 覆盖前把旧文件存入安装目录 `update_backups\yyyyMMdd_HHmmss\`。
4. 逐文件把 `payload` 直接覆盖至安装目录。
5. **不再解析、合并或回写 JSON。**

因此新补丁会恢复标准 `nikke_round_config.json` 和标准妮姬名单，用户自己的等待参数、手工名单会被重置，但旧文件在 `update_backups` 中保留。截图、导出数据、主题及自定义背景目录不在 payload 内，不会被删除。

重建命令：

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build_update_patches.ps1 -FullVersion 0.1.13 -LiteVersion 0.1.5
~~~

此脚本从 `dist\r_0.1.13` 与 `dist\lite_r_0.1.5` 读取 payload，**不是**从开发源码直接取文件。这样避免把开发中的 GPU/性能偏好配置发布给用户；发行目录内标准配置是 CPU/安全默认值。

构建后至少检查：

- 每个 ZIP 只有一个正确的 `payload\nikke_round_config.json`。
- ZIP 不含旧 JSON 合并逻辑、`metadata` 合并文件、`__pycache__` 或 `.pyc`。
- 模拟旧安装目录后执行补丁，payload 每个文件的 SHA-256 都应和发行目录同名文件一致。
- 人为写坏的二维配置能被标准配置完整替换。

当前 `0.1.13`/`0.1.5` 补丁已经按上述方式验证；它们可直接修复此前旧补丁产生的坏二维配置，不需要额外单独发布“修复补丁”。

## 10. 近期变更（相对完整 0.1.11 / 轻量 0.1.4）

| 时间（UTC+8） | 更新 |
| --- | --- |
| 2026-07-15 13:03 | OCR 循环等级支持 1 至 999，加入合并文本复核、数值二次确认与尾部字形校验，修复部分 99 被读成 66。 |
| 2026-07-15 下午 | 两版本加入图像工具：JPEG 压缩、横纵拼图；更新任务栏图标。 |
| 2026-07-15 下午 | 加入国服/国际服/港澳台服进程检测、GUI 状态显示和截图文件服务器后缀。 |
| 2026-07-15 下午 | 国际服/HMT 关闭弹窗由 Esc 改为点击侧边空白；晋级赛转冠军争霸赛改为左下返回按钮。 |
| 2026-07-15 下午 | 详细战果页加入轮询，连续两次完整后固定等待 0.5 秒再重新截图裁切；超时网络提示。 |
| 2026-07-15 14:05 | 国际服/HMT 单独裁切详细页，移除蓝色标题带/底部残留；补齐循环等级辅助型右侧边缘。国服不变。 |
| 2026-07-15 下午 | 头像详情页等待、出线图打开简化赛果等待均独立为可保存参数，后者默认 1 秒。 |
| 2026-07-15 17:08 | 升级补丁改为备份后直接覆盖，修复旧 JSON 深合并破坏二维坐标的问题。 |
| 2026-07-15 17:11 | 重建完整版/轻量版直接替换补丁并完成 SHA-256 覆盖审计。 |

早前部分记录未保留准确分钟，不能伪造。今后发版时请将新增日志写到真实分钟。

## 11. 风险、未完成项与推荐动作

### 已知风险

1. 国际服/HMT UI 将来可能更新。黑色详细赛果按钮、`DISCONNECTED` 页、侧边关闭区、返回按钮都可能失效。遇到卡住先保存全屏图和 `screenshots\logs` 日志，再按服务器局部修正；不要直接改国服。
2. 国服未来更新也可能出现同类详细页差异。当前国服严格逻辑故意不动。
3. 自动截图不正式支持 `2560x1600`，仅 OCR 图像解析支持该尺寸。
4. OCR 对低清图、重压 JPEG、网络导致的 `DISCONNECTED` 卡面仍可能误识别。图像工具压 JPEG 适合节省空间，战斗 OCR 优先使用原 PNG。
5. 补丁会重置配置/名单。日后若需保留用户参数，必须另行设计“了解具体 schema 的安全迁移器”，不能恢复 PowerShell 泛用深合并。

### 明确不要做

- 未经用户明确要求，不要自行封装、重建安装包或发布版本。
- 不要把 CUDA/cuDNN/NVIDIA runtime 打进安装包或公开 Git。
- 不要恢复为避开版权而删除的图片。
- 不要把手工 OCR 导出优化与自动截图 OCR 匹配混为一谈。
- 不要让轻量版隐式依赖 PaddleOCR、GPU 或用户系统 Python。
- 不要为了“干净”重置 Git 工作树。
- 不要把国际服/HMT 的关闭和转场重新改成 Esc。
- 不要将 `runtime_*`、安装包、截图日志、私有自定义背景推送公开仓库。

### 推荐下一步工作法

1. 先确认用户的请求属于 GUI、自动截图、OCR、封装还是补丁，避免跨边界重构。
2. 改自动截图前，分开确认国服、国际服、港澳台服影响，优先用 `server` 局部条件。
3. 改 OCR 前，以少量图核对 Excel/JSON 字段、64 人 Sheet2 和循环等级，再讨论性能。
4. 用户要求发版时：先构建 release directory、验证、安装至非开发目录实测，再构建安装包、最后重建补丁。
5. 每次补丁都要模拟完整/轻量安装路径，尤其要检查 `nikke_round_config.json` 的二维数组。

## 12. 快速定位

| 要改什么 | 先看哪里 |
| --- | --- |
| 主 GUI、主题、设置、OCR 任务窗 | `nikke_gui_launcher.ps1` |
| 轻量 GUI、OCR Demo 禁用 | `nikke_capture_lite_launcher.ps1` |
| 鼠标点击、服务器差异、轮询、拼图 | `nikke_round_stitcher.py` |
| 坐标、裁切、等待参数 | `nikke_round_config.json` |
| 图像压缩/拼接 | `nikke_image_tools.py` |
| OCR CLI、四图排序、导出入口 | `dataanalysis\arena_ocr_tool\main.py` |
| 循环等级/战力/阵容解析 | `dataanalysis\arena_ocr_tool\recognizer\result_parser.py` |
| 妮姬名和别名 | `dataanalysis\arena_ocr_tool\data\nikke_names.json` |
| 完整版发布 | `tools\build_release_directory.ps1`、`tools\build_installer.ps1`、`installer\NIKKE_Arena_Tool.iss` |
| 轻量版发布 | `tools\build_capture_lite_release.ps1`、`tools\build_capture_lite_installer.ps1`、`installer\NIKKE_Arena_Capture_Lite.iss` |
| 更新补丁 | `tools\build_update_patches.ps1` |

## 13. 新对话开始时的最小检查

~~~powershell
Set-Location 'C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs'

# 只检查状态，不自动还原
git status --short

# Python 语法检查：不触发真实鼠标点击
.\runtime_core\python.exe -m py_compile .\nikke_round_stitcher.py .\nikke_image_tools.py .\dataanalysis\arena_ocr_tool\main.py .\dataanalysis\arena_ocr_tool\recognizer\result_parser.py

# 当前升级补丁
Get-ChildItem .\dist\updates
~~~

若开发根目录没有 `runtime_core`，不要直接重建；先确认是否应在 `dist\r_0.1.13` 中验证，以及用户是否要求重建 runtime/封装。

## 14. 作者与权属

- 产品方向、项目所有权与决策：**夙辛**（GitHub：`iiwm5458`）。
- 工程协作、封装支持与本交接文档：**Codex（GPT-5）**。

Codex 是 AI 工程协作工具，不主张项目所有权。NIKKE 游戏素材、第三方库、PaddleOCR 模型、网站图标和 NVIDIA 相关组件均受各自许可约束；再发布前应单独核对。
