# 正式封装验证记录：Full 0.1.25 / Lite 0.1.15

日期：2026-10-05（Asia/Shanghai）

## 产物与原因说明

独立交付目录：`deliveries/NIKKE_C_ARENA_20261005_Full0.1.25_Lite0.1.15`。

| 产物 | 字节数 |
| --- | ---: |
| NIKKE_Arena_Tool_Setup_0.1.25.exe | 272813195 |
| NIKKE_Arena_Capture_Lite_Setup_0.1.15.exe | 33726479 |
| NIKKE_C_ARENA_Tool_完整版_升级补丁_0.1.25.zip | 93608766 |
| NIKKE_C_ARENA_Capture_Lite_轻量版_升级补丁_0.1.15.zip | 20919838 |

两版 EXE 的产品版本分别为 0.1.25、0.1.15。交付目录有 SHA256SUMS.txt，每个交付副本与构建产物哈希相同。

安装器每次默认显示 C 盘约定目录，允许手动选择；补丁只更新所选已有安装目录，不迁移工具。两版更新记录详细列出安装位置、历史路径、混装/权限检查、轻量版翻译和语言按钮修正等原因；完整版额外说明根目录受限宿主兼容与旧 AppData MOD 的重新安装要求。

## 构建验证

- 沿用现有 build_installer.ps1 / build_capture_lite_installer.ps1，显式指定新版本和已安装的 Inno Setup 6.7.3。
- Full：12 项受限宿主测试通过；核心 PIL、CPU PaddleOCR 2.6.2、纯 Python 3.10 基础环境、离线 OCR 模型初始化及 GUI -Check 通过；随后清理发行字节码并编译正式安装器。
- Lite：截图与图像工具运行依赖、GUI -Check 和排除项验证通过；随后编译正式安装器。最终 GUI 与源码一致，另外运行实际模板多语言测试，523 项通过。
- 新安装配置不启用 MOD；Lite 不包含宿主或 input_plugin_id 配置。
- 安装脚本与封装前备份一致，保留 DefaultDirName、UsePreviousAppDir=no、DisableDirPage=no、原 AppId 和最低权限策略；这些目录行为先前的 14 项原生默认路径检查与 28 项原生目录检查已通过。

构建日志：`work/build_full_0.1.25_20261005.log`、`work/build_lite_0.1.15_20261005.log`、`work/build_updates_full_0.1.25_lite_0.1.15_20261005.log`。

## 跨历史真实覆盖

补丁是完整程序/资源累计覆盖，无源版本号限制；Full 对标准名单专用合并，对最早缺失 Python 基础目录仅补齐，已有运行环境不覆盖。两个补丁宣告支持各自所有已发布旧版（0.1.0 及以后），无需逐级更新。

对本地实际保留的历史目录分别建立普通复制副本，执行真实 apply_update.ps1 两次：

- Full 14 份：0.1.0、0.1.6、0.1.13–0.1.24。
- Lite 11 份：0.1.0、0.1.5–0.1.14。

全部通过。逐文件核验程序载荷、目标版本、旧程序备份，以及配置、背景、截图、日志、导出和运行环境标记；Full 额外验证自定义名单、名单恢复文件、MOD 文件、GPU 标记和最早缺失基础环境的补齐。重复更新保留最初备份和用户数据，原历史目录只读校验不变。未本地保留的中间版本没有声称逐版实测。

报告：

- `dist/isolated_0.1.25_history_c7abae36d9414259b6cb9c5d978d9a2e/history_update_report.json`。
- `dist/isolated_lite_0.1.15_history_0ed79243f1b74f1e9009de07ba3300ae/lite_history_update_report.json`。

## 独立 MOD 和产物边界

在另一隔离副本安装旧核准 beta.1 核心文件，真实应用 Full 补丁两次，仅执行 worker 的 --list-input-plugins。根目录 MOD 可发现；6 个安装目录受保护文件和 2 个假 AppData 副本哈希保持不变。没有加载后端、连接虚拟鼠标、修复驱动或发送输入。报告：`work/release_mod_preservation_7cf66a64974f45e396e0593e546c2554/report.json`。

Full 正式载荷只有通用受限宿主；不含 MOD 后端、助手、独立测试项目、G HUB 或用户 GPU runtime。Lite 额外排除宿主、OCR/Paddle 模型、CPU/GPU OCR 和硬件监控资源。标准 Python 基础环境自带的上游测试文件属于既有运行库，不是项目的罗技测试项目。

Full ZIP 1705 文件、Lite ZIP 31 文件，全部与未压缩补丁目录逐文件 SHA256 一致，内部 SHA256SUMS.txt 通过校验；私有项目路径检查通过。

## 备份及外部状态

封装前备份：`backups/release_full_0.1.25_lite_0.1.15_20261005_030108`。原 0.1.24 / Lite 0.1.14 安装器和补丁、应用源码与用户配置哈希保持不变。D 盘已安装程序的五个关键文件仍匹配修改前记录。封装阶段仅产生本地正式文件和隔离测试副本，未发布 Release 或修改已有安装。随后按用户授权同步正式源码、封装脚本和更新记录到 GitHub；私有 MOD、助手、独立测试项目及安装包/补丁不提交，Release 由项目所有者自行发布。

## 公开源码同步检查

从 GitHub 已发布的 0.1.24 正式源码提交整理新提交，只加入本次正式文件；不合并本地开发分支中的私有 MOD 或独立测试版提交历史。同步前备份 Git 引用及修改的说明文件，保留本地私有文件。

待公开源码快照含 1010 个源码/资源文件，无 MOD 目录、助手源码、独立测试项目、安装包或补丁。PowerShell 语法和差异格式检查通过；独立只读审查确认正式封装脚本没有私有构建工具依赖。

在不含私有 MOD 的公开快照中运行宿主与截图流程回归，共 17 项：16 项通过，1 项真实私有载荷校验按预期跳过，其余宿主校验使用不访问设备的模拟载荷。轻量版实际模板多语言回归再次通过全部 523 项。未连接驱动或发送实际鼠标输入。
