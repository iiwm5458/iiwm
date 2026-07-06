# OCR 模块交接文档 2026-07-01

本文用于新的 OCR 专项对话框接手“战斗图像识别”的性能、内存和准确率问题。当前对话框后续主要处理 GUI 设计和其它非 OCR 功能。

## 任务边界

- 本文只记录现状和分析，没有修改 OCR 代码。
- 新对话重点看 `dataanalysis/arena_ocr_tool` 下的识别导出模块。
- 保留“单图识别”功能。GUI 选 1 张图时仍应走 `main.py --image ...` 的旧逻辑，后续还要迁移到其它按钮。
- 不要改自动化截图流程里的 OCR 判断和 OCR 拼图匹配逻辑。尤其不要为了优化导出 OCR 去动 `nikke_round_stitcher.py` 中这些链路：
  - `get_season_ocr`
  - `recognize_profile_aliases`
  - `result_name_candidates_from_screen`
  - `collect_cached_stage_results`
  - `run_season_capture`
  - `stitch_cached_stage`

自动化截图流程用 OCR 来识别/校正选手、判断胜负、决定拼图顺序。它不是这次导出 OCR 优化的目标。

## 当前用户现象

用户运行四卡槽 OCR 时出现：

```text
[launcher] OCR exception: 引发类型为“System.OutOfMemoryException”的异常。
```

已查看最近日志：

- `outputs\screenshots\2026-07-01\ocr_run_20260701_163110.log`
- `outputs\screenshots\2026-07-01\ocr_run_20260701_144651.log`

这两次四图排序已经正确，命令参数顺序为：

1. `--season-group64-image` -> `64进32全部战斗数据（详）...png`
2. `--season-group32-image` -> `32进16全部战斗数据（详）...png`
3. `--season-group16-image` -> `16进8全部战斗数据（详）...png`
4. `--season-top8-image` -> `TOP8-决赛战斗数据（详）...png`

日志都停在 `64进32全部` 的第 8/32 个 block 左右：

```text
[stdout] [image] source=64进32全部战斗数据（详）...png stage=group64 include_teams=True
[stdout] [split] source=64进32全部战斗数据（详）...png blocks=32 layout=auto
[stdout] [progress] 8/63 12.70% ... block 8/32
[launcher] OCR exception: 引发类型为“System.OutOfMemoryException”的异常。
```

由日志时间看，8 个 block 大约耗时 50 到 70 分钟。按当前速度，单独 `64进32全部` 的 32 个 block 就可能超过 3.5 小时，四图完整识别更久。

相关图片尺寸：

- `64进32全部战斗数据（详）...png`: `15184x9364`, 文件约 `194 MB`, RGB 解码后约 `426 MB`
- `32进16全部战斗数据（详）...png`: `15184x4668`, 文件约 `97 MB`
- `16进8全部战斗数据（详）...png`: `15240x2306`, 文件约 `48 MB`
- `TOP8-决赛战斗数据（详）...png`: `7630x7062`, 文件约 `62 MB`

较早的 `ocr_run_20260701_142232.log` 显示过历史问题：GUI 曾按卡槽顺序传参，导致 `TOP8-决赛` 被当成 `group64` 处理。该问题已在 GUI 中改为按文件名分类排序，但如果新对话再看到 `source=TOP8... stage=group64`，说明 GUI 或文件名分类又被破坏了。

## 当前入口

GUI 入口：

- `C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\nikke_gui_launcher.ps1`
- `Get-OcrSeasonImageKind`: 根据文件名识别 `group64/group32/group16/top8`
- `Get-OcrSeasonSelectedImageSpecs`: 自动按 `64进32 -> 32进16 -> 16进8 -> TOP8` 排序
- `Start-OcrRecognition`: 1 张图走单图识别，2/3 张禁止执行，4 张走赛季四图汇总识别

OCR CLI 入口：

- `C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\dataanalysis\arena_ocr_tool\main.py`
- 单图：`--image`
- 旧 manifest：`--manifest` 仍保留在 OCR CLI 中，但当前 GUI 中 `Test-OcrMediumMemoryMode` 返回 `false`
- 四图：
  - `--season-group64-image`
  - `--season-group32-image`
  - `--season-group16-image`
  - `--season-top8-image`

四图流程在 `main.py`：

- `SEASON_IMAGE_SPECS`
- `EXPECTED_SEASON_BLOCKS = 32 + 16 + 8 + 7 = 63`
- `run_season_images`
- `group64` 使用 `include_teams=True`，完整识别昵称、ID、阵容、战力、胜负，并构建 64 人 roster
- `group32/group16/top8` 使用 `include_teams=False`，只识别玩家昵称、ID、胜负，再通过 `group64` roster 回填阵容和战力

## 必须保留的输出数据

主表 `ArenaData` 必须保留这些字段：

- `对局轮次`
- `攻方选手`
- `攻方选手ID`
- `守方选手`
- `守方选手ID`
- `攻方P1` 到 `攻方P5`
- `攻方P1战力` 到 `攻方P5战力`
- `守方P1` 到 `守方P5`
- `守方P1战力` 到 `守方P5战力`
- `胜方`
- `置信度`
- `源图片`

Excel 还需要保留第二个 sheet：`参赛阵容`。表头为：

```text
参赛选手, 选手ID, P1, P1战力, P2, P2战力, P3, P3战力, P4, P4战力, P5, P5战力
```

导出代码位置：

- `recognizer/exporter.py`
- `HEADERS`
- `ROSTER_HEADERS`
- `build_record_key`
- `export_json`
- `export_excel`

## 必须保留的识别区域

分图区域在 `recognizer/image_splitter.py`：

- `classify_layout`
- `split_input_image`
- `split_all_groups_image`
- `split_top8_pyramid`
- `split_group_image`
- `split_match_block`

`split_match_block` 当前把单个对局块切为：

- 攻方区域：x `0.00` 到 `0.43`
- 中央胜负/详情区域：x `0.43` 到 `0.57`
- 守方区域：x `0.57` 到 `1.00`

核心 OCR 区域在 `recognizer/result_parser.py`：

- 攻方 ID：`(0.23, 0.205, 0.86, 0.245)`，fallback `(0.15, 0.19, 0.98, 0.255)`
- 守方 ID：`(0.02, 0.205, 0.76, 0.245)`，fallback `(0.02, 0.19, 0.85, 0.255)`
- 攻方昵称：`(0.20, 0.172, 0.74, 0.202)`
- 守方昵称：`(0.12, 0.172, 0.67, 0.202)`
- 阵容行区域：y `0.275` 到 `0.925`，均分为 5 行
- 行内整体 OCR crop：x `0.01` 到 `0.99`

卡位中心：

```text
ATTACKER_CARD_SLOT_CENTERS = (0.14, 0.30, 0.49, 0.69, 0.87)
DEFENDER_CARD_SLOT_CENTERS = (0.215, 0.385, 0.555, 0.725, 0.895)
ATTACKER_POWER_SLOT_CENTERS = (0.169, 0.338, 0.507, 0.677, 0.845)
DEFENDER_POWER_SLOT_CENTERS = (0.144, 0.313, 0.482, 0.651, 0.819)
DETAIL_SLOT_CENTERS = (0.109, 0.291, 0.473, 0.655, 0.837)
```

战力精细裁剪框在 `_recognize_power_from_slot`，含义是围绕 `center` 的相对 crop：

```text
(0.135, 0.64, 0.105, 0.995)
(0.125, 0.68, 0.100, 0.995)
(0.150, 0.58, 0.115, 0.995)
(0.110, 0.72, 0.095, 0.995)
(0.170, 0.60, 0.125, 0.995)
```

实际 crop 为：

```text
(center - left, top, center + right, bottom)
```

胜负判断在 `detect_round_winner`：

- 优先读中央 detail 文本中的 `WIN/LOSE`
- 失败时用颜色检测左右胜负区域

这些区域是前一个对话已经调过的识别基础，新对话优化性能时应尽量保持区域不变；如果必须改，需要用真实截图逐项验证昵称、ID、阵容、战力、胜负。

## 为什么现在很慢

当前慢的主因不是“还在导出 manifest 图片”。现状是：

- 自动截图流程的 manifest 图片/manifest 导出已移除。
- GUI 的 manifest 中内存模式被停用，`Test-OcrMediumMemoryMode` 直接返回 `false`。
- OCR CLI 中仍保留 `--manifest` 兼容旧数据，但四卡槽识别没有走 manifest。

真正的性能热点在 `result_parser.py` 的 `group64 include_teams=True` 分支，尤其是战力 OCR。

每个 `64进32` match block 内部大致会做：

- 2 个玩家 ID OCR，带 fallback
- 2 个玩家昵称 OCR，昵称会调用中文 detection 以及日/韩/中文 recognition-only 模型候选
- 攻守双方各 5 行阵容 OCR
- 中央 detail 5 行 OCR
- 5 行胜负判断
- 战力精细 OCR

战力精细 OCR 是最大瓶颈：

- 每个 block 有 2 边 x 5 行 x 5 卡位 = 50 个战力槽
- 每个战力槽 `_recognize_power_from_slot` 会尝试 5 个 crop box
- adaptive 模式下每个 crop 最多 5 个预处理变体
- 最坏约 50 x 5 x 5 = 1250 次 PaddleOCR 调用，仅用于一个 block 的战力
- `64进32` 有 32 个 block，战力部分最坏可到约 40000 次 PaddleOCR 调用

`_power_preprocess_variants` 还会做 x4 放大、padding、autocontrast、contrast、threshold 等多个图像变体。很多小图之后又会经过 `prepare_for_ocr`，当最大边小于 1800 时再次 x2 放大。这个组合会显著增加 CPU 时间和临时内存。

`64进32全部` 大图本身是 `15184x9364`，RGB 解码后约 `426 MB`。`split_all_groups_image` 会生成并保留 32 个 block image，再加上 PaddleOCR 模型、昵称额外模型、NumPy 数组、预处理变体和 Paddle 内部缓存，内存压力会持续叠加。OOM 出现在第 8 个 block 左右，很像 Paddle/NumPy/PIL 的临时对象或内部缓存没有及时回落，累积到系统内存不足。

性能档位和 CPU 线程限制已按用户要求停用。当前只支持 CPU/GPU 切换，不再设置 `--cpu-threads`，也不再写 `OMP_NUM_THREADS/MKL_NUM_THREADS`。这符合 GUI 需求，但 PaddleOCR 默认线程策略可能会放大内存和 CPU 竞争。

## OOM 的判断

日志前缀是 `[launcher] OCR exception`，说明异常是在 PowerShell/WPF 启动器层捕获到的 `.NET System.OutOfMemoryException`。这不一定表示 Python 进程直接抛出了 .NET 异常，更可能是：

- Python/PaddleOCR 子进程占用大量内存；
- 系统剩余内存不足；
- 启动器在刷新 UI、追加日志、读取 stdout/stderr、写运行日志或创建字符串时也分配失败；
- 因此异常显示在 launcher 层。

当前日志内容很短，`capturedLines` 本身不是这两次 OOM 的直接主因。但 `capturedLines` 是无界 `List[string]`，后续仍建议改成只保留尾部日志，避免长任务时增加不必要风险。

## 下一对话建议优先级

先不要大范围重写。建议按这个顺序做：

1. 加性能/内存埋点，不改识别行为。
   - 统计每个 block 耗时。
   - 统计每类 OCR 调用次数：ID、昵称、阵容行、detail、战力 crop/variant。
   - 记录 Python 进程 RSS 内存，确认是否每个 block 后持续上涨。

2. 降低战力 OCR 调用爆炸。
   - 先用 row-level OCR 的 `_match_power_slots`。
   - 只对缺失或疑似漏首位的槽位做精细 crop fallback。
   - 精细 crop 一旦得到可信候选就早停。
   - 尝试减少 5 个 box 或 5 个 variant 的组合数量。
   - 可考虑把一整行 5 个战力数字合并成一次 OCR，再按 x 坐标分槽。

3. 降低图像内存占用。
   - 不要一次性持有 32 个 block image；改成生成器逐块处理，处理完关闭 block image。
   - 处理完每个 block 后显式关闭临时 image，并 `gc.collect()`。
   - 谨慎处理 Pillow crop 的引用/复制行为，避免大图被 block 长时间引用。

4. 检查 PaddleOCR 模型复用和昵称模型。
   - `ArenaOCRRecognizer` 主 PaddleOCR reader 常驻。
   - 日文/韩文昵称 reader 懒加载后常驻，会增加内存。
   - 如果昵称准确率允许，可考虑延迟到昵称 OCR 失败时再加载额外语言模型，或做开关。

5. 修 launcher 侧长任务日志内存。
   - `capturedLines` 改成固定容量 ring buffer。
   - UI log 已有 50000 字符裁剪，但 capturedLines 没有上限。

6. 如果考虑恢复 manifest/小块模式，必须与自动化截图流程隔离。
   - 可以在 OCR 工具内部做临时分块，不要重新让 `nikke_round_stitcher.py` 导出 manifest。
   - 不要修改自动化截图中的 OCR 选手匹配和根据 OCR 结果拼图的流程。

## 验证清单

新对话修改 OCR 后至少验证：

- 单图识别仍能运行：`main.py --image ...`
- 四图识别仍按文件名排序：`64进32 -> 32进16 -> 16进8 -> TOP8`
- `64进32` 仍能输出 64 名玩家 roster 到 Excel 第二个 sheet `参赛阵容`
- `group32/group16/top8` 仍只识别 ID、昵称、胜负，再从 roster 回填阵容和战力
- JSON 和 Excel 主表字段不丢失
- `nikke_round_stitcher.py` 自动截图 OCR 匹配/拼图流程没有被改动
- 编译检查：

```powershell
python -m py_compile `
  "C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\dataanalysis\arena_ocr_tool\main.py" `
  "C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\dataanalysis\arena_ocr_tool\recognizer\arena_ocr.py" `
  "C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\dataanalysis\arena_ocr_tool\recognizer\image_splitter.py" `
  "C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\dataanalysis\arena_ocr_tool\recognizer\result_parser.py" `
  "C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\dataanalysis\arena_ocr_tool\recognizer\exporter.py"
```

## 重要文件索引

- GUI：`C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\nikke_gui_launcher.ps1`
- OCR CLI：`C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\dataanalysis\arena_ocr_tool\main.py`
- OCR wrapper：`C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\dataanalysis\arena_ocr_tool\recognizer\arena_ocr.py`
- 分图：`C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\dataanalysis\arena_ocr_tool\recognizer\image_splitter.py`
- 识别解析：`C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\dataanalysis\arena_ocr_tool\recognizer\result_parser.py`
- 导出：`C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\dataanalysis\arena_ocr_tool\recognizer\exporter.py`
- 自动截图/拼图流程：`C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs\nikke_round_stitcher.py`

