# 自动截图拼图工具

## 图形界面

推荐直接打开图形界面：

```powershell
cd "C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs"
.\run_gui.bat
```

窗口里的 `单人竞技场信息` 按钮会自动：

1. 查找并切换到 `nikke.exe` 游戏窗口。
2. 等待 1 秒。
3. 执行单人竞技场信息截图和拼接。
4. 把成品保存到当前 `outputs` 文件夹。

`打开截图文件夹` 按钮会直接打开保存截图的目录。

GUI 使用 Windows 原生 WPF，不依赖 Tkinter。背景图位于 `assets/gui_background.png`，当前由 `assets/pixiewall-nh8jdt-3840x2160.jpg` 转换而来。

这个小工具会自动完成：

1. 依次点击 `Round 01` 到 `Round 05`。
2. 每轮截图阵容区域。
3. 点击用户头像打开资料页。
4. 截取资料页顶部的用户基础信息区域。
5. 截取基础页的部队战斗力、作战人员、时装、部队现状。
6. 点击前哨基地页签并截取研究等级区域。
7. 把这些信息放在最上方，下面按 Round 01-05 纵向拼成长图。

## 使用前准备

先把游戏停在你截图 1 那种界面：竞技场信息弹窗已经打开，并且能看到头像和 `Round 01` 到 `Round 05` 按钮。

建议游戏保持和截图一样的全屏比例。默认坐标按你提供的原图尺寸 `3440x1440` 设置；如果你的屏幕尺寸不同，程序会按比例自动缩放坐标。

## 运行

在这个目录打开 PowerShell：

```powershell
cd "C:\Users\iiwm\Documents\Codex\2026-06-06\files-mentioned-by-the-user-qq\outputs"
.\run_stitcher.bat
```

程序会倒计时 3 秒。倒计时期间把游戏窗口放到前台，不要移动鼠标。

完成后会在同目录生成类似：

```text
nikke_stitched_20260606_230000.png
```

## 先检查截图范围

如果担心坐标不准，先运行预览：

```powershell
.\run_stitcher.bat --preview --output .\preview_regions.png
```

它不会点击，只会保存一张标注图：

- 红框：资料页基础信息截图范围
- 青框：每个 Round 阵容截图范围
- 黄点：Round 按钮点击位置
- 绿点：头像和资料页关闭按钮点击位置

## 微调坐标

坐标都在 `nikke_round_config.json` 里。

```json
"clicks": {
  "avatar": [1477, 579],
  "profile_close": [2049, 138],
  "outpost_tab": [1899, 1333],
  "round_tabs": {
    "1": [1462, 707],
    "2": [1604, 707],
    "3": [1754, 707],
    "4": [1900, 707],
    "5": [2001, 707]
  }
},
"crops": {
  "round_lineup": [1393, 756, 660, 274],
  "profile_basic": [1378, 0, 684, 514],
  "team_summary": [1378, 908, 684, 104],
  "outpost_research": [1403, 976, 634, 255]
}
```

截图区域格式是：

```text
[左上角 x, 左上角 y, 宽度, 高度]
```

如果你想查看鼠标当前坐标：

```powershell
.\run_stitcher.bat --mouse-pos
```

把鼠标移到目标位置，记下显示的 `x/y`，按 `Ctrl+C` 结束。

## 可选设置

`output_width` 控制最终长图宽度，默认 `720`。

`save_parts` 改成 `true` 后，会同时保存单独的资料截图和 5 张 Round 截图，方便调试。

如果不想截图后自动关闭资料页，把 `close_profile_after_capture` 改成 `false`。

## 依赖

脚本只需要 Python 和 Pillow。推荐直接运行 `run_stitcher.bat`，它会优先使用 Codex 自带的 Python 环境。如果换到别的电脑运行时提示缺少 Pillow：

```powershell
python -m pip install pillow
```

## 分辨率自适应

配置文件里的 `coordinate_mode` 默认是：

```json
"coordinate_mode": "centered_height"
```

这个模式会按当前截图高度等比缩放坐标，然后把游戏 UI 按屏幕中心对齐。它适合 NIKKE 这类中心弹窗固定、左右背景随分辨率变化的界面，常见的 `3440x1440`、`2560x1440`、`1920x1080` 都可以自动换算。

如果你故意想使用旧版“按宽高分别拉伸”的算法，可以改成：

```json
"coordinate_mode": "stretch"
```

换分辨率后建议先运行一次预览：

```powershell
.\run_stitcher.bat --preview --output .\preview_regions.png
```

终端会显示当前屏幕尺寸、缩放比例和偏移量，预览图里也会标出实际点击点和截图框。
