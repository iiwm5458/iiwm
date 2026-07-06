# 角色详情自动截图拼接

这个工具会从角色列表页开始，自动执行你描述的流程：

1. 检查并打开爆裂 I 筛选。
2. 截取第一行左侧第一个角色卡。
3. 进入角色详情页，截取收藏品区、战斗力与属性区。
4. 依次点击头部、身躯、手臂、腿部装备，分别截取装备图片和词条，随后按 Esc 关闭装备弹窗。
5. 点击技能页签并截取技能区。
6. 将所有截图从左到右拼接成一张图片。

## 运行

先把游戏停在角色列表页，也就是你图 1 的界面。然后运行：

```powershell
cd "C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs"
.\run_character_capture.bat
```

脚本默认倒计时 3 秒。倒计时期间把游戏窗口放到前台，不要移动鼠标。

成品会保存到：

```text
outputs\screenshots\日期\nikke_character_时间.png
```

如果 `save_parts` 为 `true`，同名文件夹里还会保存每一块单独截图，方便校准。

## 分辨率自适应

配置文件是 `nikke_character_capture_config.json`。基准分辨率为 `3440x1440`，默认使用：

```json
"coordinate_mode": "height_anchored"
```

这个模式按当前屏幕高度缩放，并给每个区域设置锚点：

- `left`：左侧角色卡、收藏品区。
- `right`：右侧属性、装备槽、技能区。
- `center`：顶部筛选按钮和中间装备弹窗。

因此在不同宽高比下，比单纯按宽高拉伸更不容易偏。

## 预览校准

可以先生成一张标注图，不会点击游戏：

```powershell
.\run_character_capture.bat --preview --output .\character_preview.png
```

如果某个点或截图框偏了，修改 `nikke_character_capture_config.json` 里的 `clicks` 或 `crops`。截图框格式是：

```text
[左上角 x, 左上角 y, 宽度, 高度]
```

查看当前鼠标坐标：

```powershell
.\run_character_capture.bat --mouse-pos
```

如果游戏不响应点击，请右键以管理员身份运行脚本或命令行。

## 装备识别与加载等待

点击角色进入详情页后，脚本会额外等待 `after_profile_load_seconds`，默认 `1.5` 秒，避免加载动画还没结束就开始点击装备。

装备处理规则：

- 先检测右侧装备槽是否为空；空槽不点击、不输出。
- 打开装备弹窗后，会在弹窗中动态定位装备图标位置，不再依赖固定职业坐标。
- 点击装备后会验证中央弹窗是否真正打开；失败时会换点击位置重试，仍失败则跳过该槽，避免把人物立绘误识别成装备。
- 装备弹窗高度不同时，程序会识别白色弹窗实际边界并动态点击右上角关闭按钮，不再使用固定关闭坐标。
- 如果检测到词条锁图标，就输出“装备图标 + 词条”。
- 如果没有检测到词条，例如 T9 黄色装备，只输出装备图标。
- 职业标签模板在 `assets/equipment_type_fire.png`、`assets/equipment_type_defense.png`、`assets/equipment_type_support.png`，主要用于日志和后续扩展。

技能页处理规则：

- 点击技能页签后会检查技能截图的彩色比例。
- 如果截图明显像装备格，会自动重试点击技能页签，避免把装备页误当成技能页保存。

## 固定模板尺寸

最终成品固定使用 `001.png` 的模板尺寸 `2842x342`。角色卡、收藏品、战斗力、技能和装备四宫格都有固定位置。

- 每个装备单元固定为 `743x148`。
- 装备图标固定占左侧 `190x148`。
- 词条固定占右侧 `549x148`。
- 没有词条时只放装备图标，词条区域保持空白。
- 没有装备时对应装备单元保持空白，不会移动其它装备或改变成品尺寸。

## 封装提示

脚本只依赖 Python 标准库和 Pillow，适合用 PyInstaller 打包。打包时需要把 `assets` 目录一起带上，例如：

```powershell
pyinstaller --onefile --add-data "assets;assets" nikke_character_capture.py
```

## 批量导出全部角色

从角色列表页开始运行：

```powershell
cd "C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs"
.\run_all_characters.bat
```

建议第一次先试跑 3 个角色：

```powershell
.\run_all_characters.bat --max-characters 3
```

批量模式会按可见列表从左到右、从上到下点击角色。由于屏幕不能一次显示全部角色，它每次只处理完整可见的两行，然后向下滚动；滚动后会保留一行左右的重叠，并用角色卡截图的感知哈希去重。这样重叠行不会重复导出，滚动距离略有误差时也不容易漏掉角色。

如果发现滚动后跳得太多，把 `nikke_character_capture_config.json` 里的：

```json
"scroll_wheel_clicks": -5
```

改成 `-3` 或 `-2`。如果发现同一个角色重复导出，可以把：

```json
"duplicate_hamming_threshold": 24
```

适当调大一点，比如 `30`。
