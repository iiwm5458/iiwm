param([switch]$Check)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AssetsDir = Join-Path $ScriptDir "assets"
$DarkBackgroundPath = Join-Path $AssetsDir "pixiewall-nh8jdt-3840x2160.jpg"
$PinkBackgroundPath = Join-Path $AssetsDir "D40E44B0E0C341D691DF26CA85E5E285.jpg"
$MarianFramePath = Join-Path $AssetsDir "single_marian_bg.jpg"
$DoroFramePath = Join-Path $AssetsDir "single_doro_bg.jpg"
$CinderellaFramePath = Join-Path $AssetsDir "single_cinderella_bg.jpg"
$SupportMarianFramePath = Join-Path $AssetsDir "support_marian_bg.jpg"
$SupportDoroFramePath = Join-Path $AssetsDir "support_doro_bg.jpg"
$SupportCinderellaFramePath = Join-Path $AssetsDir "support_cinderella_bg.jpg"
$GroupMarianFramePath = Join-Path $AssetsDir "group_marian_bg.jpg"
$GroupDoroFramePath = Join-Path $AssetsDir "group_doro_bg.jpg"
$GroupCinderellaFramePath = Join-Path $AssetsDir "group_cinderella_bg.jpg"
$CustomFrameDir = Join-Path $ScriptDir "custom_backgrounds"
$SupportCustomFrameDir = Join-Path $ScriptDir "support_custom_backgrounds"
$GroupCustomFrameDir = Join-Path $ScriptDir "group_custom_backgrounds"
$OutputRoot = Join-Path $ScriptDir "screenshots"
$ExamplePath = Join-Path $AssetsDir "arena_info_example.png"
$SupportExamplePath = Join-Path $AssetsDir "support_info_example.png"
$GroupExamplePath = Join-Path $AssetsDir "group_info_example.png"
$Top8ExamplePath = Join-Path $AssetsDir "top8_info_example.png"
$DoroPath = Join-Path $AssetsDir "doro_theme_button.png"
$AppIconPath = Join-Path $AssetsDir "app_doro_commander.ico"
$StitcherPath = Join-Path $ScriptDir "nikke_round_stitcher.py"
$RoundConfigPath = Join-Path $ScriptDir "nikke_round_config.json"
$DataAnalysisDir = Join-Path $ScriptDir "dataanalysis"
$OcrToolPath = Join-Path $DataAnalysisDir "arena_ocr_tool\main.py"
$NikkeNameListPath = Join-Path $DataAnalysisDir "arena_ocr_tool\data\nikke_names.json"
$OcrExampleFile = '"\u4f8b\u56fe1.png"' | ConvertFrom-Json
$DefaultOcrFile = '"64\u5f3a-\u6211\u8981\u6240\u6709\u4eba\uff08GROUP\uff09\u7684\u6570\u636e.png"' | ConvertFrom-Json
$OcrExamplePath = Join-Path $DataAnalysisDir $OcrExampleFile
$DefaultOcrImagePath = Join-Path $DataAnalysisDir $DefaultOcrFile
$SelectedOcrImagePath = $DefaultOcrImagePath
$OcrSlotReadyIconPath = Join-Path $AssetsDir "ocr_slot_ready.png"
$OcrSlotEmptyImagePath = Join-Path $AssetsDir "ocr_slot_empty.png"
$OcrSlotSelectedImagePath = Join-Path $AssetsDir "ocr_slot_selected.png"
$SiteSkyxmoonIconPath = Join-Path $AssetsDir "site_nikke_skyxmoon.png"
$SiteNikkeTopIconPath = Join-Path $AssetsDir "site_nikke_top.png"
$SiteMerlotJjcIconPath = Join-Path $AssetsDir "site_merlot_jjc.png"
$SiteGamekeeNikkeIconPath = Join-Path $AssetsDir "site_gamekee_nikke.png"
$SiteBilibiliGuseIconPath = Join-Path $AssetsDir "site_bilibili_guse.png"
$SiteBilibiliDeen33IconPath = Join-Path $AssetsDir "site_bilibili_deen33.png"
$OcrSeasonImageSlots = @{
    top8 = $null
    group16 = $null
    group32 = $null
    group64 = $null
}
$RoundWorkerExe = Join-Path $ScriptDir "nikke_round_stitcher_worker.exe"
$BundledCorePython = Join-Path $ScriptDir "runtime_core\python.exe"
$BundledCpuPython = Join-Path $ScriptDir "runtime_cpu\python.exe"
$BundledOcrGpuPython = Join-Path $ScriptDir "runtime_gpu\Scripts\python.exe"

function Test-PythonWorkerRuntime($Path) {
    if (-not $Path -or -not (Test-Path $Path) -or ($Path -like "*\WindowsApps\*")) {
        return $false
    }
    try {
        & $Path -c "from PIL import Image, ImageDraw, ImageFilter, ImageGrab" *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Resolve-PythonExe {
    $candidates = @()
    $candidates += $BundledCorePython
    $candidates += $BundledCpuPython
    if ($env:LOCALAPPDATA) {
        $candidates += Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
        $pythonRoot = Join-Path $env:LOCALAPPDATA "Programs\Python"
        if (Test-Path $pythonRoot) {
            $candidates += Get-ChildItem -LiteralPath $pythonRoot -Directory -Filter "Python*" -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending |
                ForEach-Object { Join-Path $_.FullName "python.exe" }
        }
    }
    foreach ($candidate in $candidates) {
        if (Test-PythonWorkerRuntime $candidate) {
            return $candidate
        }
    }
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source -and (Test-PythonWorkerRuntime $command.Source)) {
        return $command.Source
    }
    return $null
}

$PythonExe = Resolve-PythonExe

function Test-PythonOcrRuntime($Path) {
    if (-not $Path -or -not (Test-Path $Path)) {
        return $false
    }
    try {
        & $Path -c "from PIL import Image; import paddleocr, paddle, cv2, numpy" *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Resolve-OcrPythonExe {
    $candidates = @()
    if ($env:NIKKE_OCR_PYTHON) {
        $candidates += $env:NIKKE_OCR_PYTHON
    }
    $candidates += $BundledCpuPython
    if ($env:LOCALAPPDATA) {
        $pythonRoot = Join-Path $env:LOCALAPPDATA "Programs\Python"
        if (Test-Path $pythonRoot) {
            $candidates += Get-ChildItem -LiteralPath $pythonRoot -Directory -Filter "Python*" -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending |
                ForEach-Object { Join-Path $_.FullName "python.exe" }
        }
    }

    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source) {
        try {
            $resolved = (& $command.Source -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1)
            if ($resolved) {
                $candidates += $resolved.Trim()
            }
        } catch {}
        $candidates += $command.Source
    }

    $candidates += $PythonExe
    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        if (Test-PythonOcrRuntime $candidate) {
            return $candidate
        }
    }
    return $null
}

$OcrPythonExe = Resolve-OcrPythonExe
$OcrGpuPythonExe = $null
$ActiveOcrPythonExe = $null

function Test-OcrGpuRuntime($Path) {
    if (-not $Path -or -not (Test-Path $Path)) {
        return $false
    }
    try {
        & $Path -c "import paddle,sys; sys.exit(0 if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0 else 1)" *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Resolve-OcrGpuPythonExe {
    $candidates = @()
    if ($env:NIKKE_OCR_GPU_PYTHON) {
        $candidates += $env:NIKKE_OCR_GPU_PYTHON
    }
    $candidates += $BundledOcrGpuPython
    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        if ((Test-PythonOcrRuntime $candidate) -and (Test-OcrGpuRuntime $candidate)) {
            return $candidate
        }
    }
    return $null
}

$OcrGpuPythonExe = Resolve-OcrGpuPythonExe
$OcrGpuAvailable = $null -ne $OcrGpuPythonExe
$OcrPerformanceMode = "full"
$LowMemoryMode = $false
$OcrMediumMemoryMode = $false
$SeasonMemoryWarnGb = 8.0

$DarkSourceUrl = "https://www.pixiewall.com/wallpaper/rapi-drake-laplace-maxwell-nikke-4k-25008"
$PinkSourceUrl = "https://www.pixiewall.com/wallpaper/alice-marchen-dream-nikke-doro-5k-29009"
$SiteSkyxmoonUrl = "https://nikke.skyxmoon.cn/"
$SiteNikkeTopUrl = "https://nikke.top/"
$SiteMerlotJjcUrl = "https://merlot-sve.xyz:17838/jjc"
$SiteGamekeeNikkeUrl = "https://www.gamekee.com/nikke/second/64581"
$SiteBilibiliGuseUrl = "https://www.bilibili.com/read/readlist/rl1058034?spm_id_from=333.1387.0.0"
$SiteBilibiliDeen33Url = "https://www.bilibili.com/read/readlist/rl1020764?spm_id_from=333.1369.opus.module_collection.click"
$CurrentTheme = "dark"
$CurrentCaptureMode = "single"
$ActiveCaptureProcess = $null
$StopRequested = $false
$OcrThermalMode = "safe"
$OcrSafeCooldownSeconds = 0.30
$OcrControlFile = $null
$OcrStopRequestTime = $null
$OcrForceStopPromptShown = $false
$OcrResourceStatusPrefix = ""
$OcrNvidiaSmiPath = $null
$OcrNvidiaSmiResolved = $false
$OcrHidSharpLibPath = Join-Path $ScriptDir "vendor\LibreHardwareMonitorLib\HidSharp.dll"
$OcrHardwareMonitorLibPath = Join-Path $ScriptDir "vendor\LibreHardwareMonitorLib\LibreHardwareMonitorLib.dll"
$OcrHardwareMonitor = $null
$OcrHardwareMonitorInitialized = $false
$OcrHardwareMonitorAvailable = $false
$OcrHardwareMonitorError = $null
$OcrThermalPrimaryDevice = "CPU"
$OcrThermalProtectionAction = "无"
$OcrThermalPauseActive = $false
$OcrThermalResumeStableSince = $null
$OcrThermalEmergencyPromptShown = $false
$OcrThermalCurrentCooldownSeconds = 0.0
$DelayMinSeconds = 0.45
$DetailDelayMinSeconds = 0.7
$DetailCaptureDelaySeconds = 3.5
$ConfiguredCaptureDelaySeconds = $null
$ConfiguredOcrPerformanceMode = "cpu"
$ConfiguredOcrThermalMode = "safe"
try {
    if (Test-Path $RoundConfigPath) {
        $configJson = Get-Content -LiteralPath $RoundConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($null -ne $configJson.timing.after_round_click_seconds) {
            $ConfiguredCaptureDelaySeconds = [double]$configJson.timing.after_round_click_seconds
        }
        if ($null -ne $configJson.timing.after_group_detail_click_seconds) {
            $DetailCaptureDelaySeconds = [double]$configJson.timing.after_group_detail_click_seconds
        }
        if ($configJson.PSObject.Properties["launcher_settings"] -and $null -ne $configJson.launcher_settings) {
            if ($configJson.launcher_settings.PSObject.Properties["ocr_performance_mode"] -and $null -ne $configJson.launcher_settings.ocr_performance_mode) {
                $ConfiguredOcrPerformanceMode = [string]$configJson.launcher_settings.ocr_performance_mode
            }
            if ($configJson.launcher_settings.PSObject.Properties["ocr_thermal_mode"] -and $null -ne $configJson.launcher_settings.ocr_thermal_mode) {
                $ConfiguredOcrThermalMode = [string]$configJson.launcher_settings.ocr_thermal_mode
            }
        }
    }
} catch {}
if ($null -ne $ConfiguredCaptureDelaySeconds) {
    $CaptureDelaySeconds = [Math]::Max($DelayMinSeconds, [Math]::Min(5.0, [double]$ConfiguredCaptureDelaySeconds))
} else {
    $CaptureDelaySeconds = [Math]::Max($DelayMinSeconds, 0.80)
}
$script:SettingsInitialized = $false
$TextIdle = '"\u7a7a\u95f2"' | ConvertFrom-Json
$TextRunning = '"\u6b63\u5728\u6267\u884c"' | ConvertFrom-Json
$TextDoneMessage = '"\u4efb\u52a1\u5df2\u5b8c\u6210\uff0c\u613f\u547d\u8fd0\u7ad9\u5728\u4f60\u8fd9\u4e00\u8fb9\uff0c\u6307\u6325\u5b98\u3002"' | ConvertFrom-Json
$TextDoneTitle = '"\u4efb\u52a1\u5b8c\u6210"' | ConvertFrom-Json
$TextStopMessage = '"\u4efb\u52a1\u5df2\u7d27\u6025\u505c\u6b62\uff0c\u6307\u6325\u5b98"' | ConvertFrom-Json
$TextStopTitle = '"\u4efb\u52a1\u505c\u6b62"' | ConvertFrom-Json
$TextGameMissingMessage = '"\u672a\u68c0\u6d4b\u5230\u6b63\u5728\u8fd0\u884c\u7684\u80dc\u5229\u5973\u795e\u3002"' | ConvertFrom-Json
$TextGameMissingTitle = '"\u672a\u68c0\u6d4b\u5230\u6e38\u620f"' | ConvertFrom-Json
$TextLowMemoryTitle = '"\u5185\u5b58\u63d0\u9192"' | ConvertFrom-Json
$TextLowMemoryMessage = '"\u5f53\u524d\u53ef\u7528\u5185\u5b58\u8f83\u4f4e\uff0c\u6267\u884c\u8d5b\u5b63\u4e00\u952e\u91c7\u96c6\u53ef\u80fd\u5360\u7528\u8f83\u591a\u5185\u5b58\u3002\u5efa\u8bae\u5148\u5173\u95ed\u5176\u5b83\u7a0b\u5e8f\uff0c\u5e76\u5728\u201c\u622a\u56fe\u4e0e\u6570\u636e\u8bc6\u522b\u53c2\u6570\u8bbe\u7f6e\u201d\u4e2d\u542f\u7528\u4f4e\u5185\u5b58\u6a21\u5f0f\u3002"' | ConvertFrom-Json
$TextArenaHelp = '"\u8bf7\u6307\u6325\u5b98\u5148\u6253\u5f00\u51a0\u519b\u7ade\u6280\u573a\u6307\u5b9a\u53c2\u8d5b\u8005\u4fe1\u606f\uff08\u5982\u56fe\uff09\u540e\u518d\u6267\u884c\u622a\u56fe"' | ConvertFrom-Json
$TextSupportHelp = '"\u8bf7\u6307\u6325\u5b98\u6253\u5f00\u5e94\u63f4\u4fe1\u606f\u754c\u9762\u540e\u518d\u6267\u884c\u622a\u56fe\uff08\u4ec5\u8d5b\u524d\u6709\u6548\uff09"' | ConvertFrom-Json
$TextGroupHelp = '"\u8bf7\u6307\u6325\u5b98\u572864\u5f3a/32\u5f3a/16\u5f3a\u7684GROUP\u5bf9\u9635\u4e2d\u6253\u5f00\u4e0b\u65b9\u9875\u9762\u540e\u518d\u6267\u884c\u622a\u56fe"' | ConvertFrom-Json
$TextTop8Help = '"\u8bf7\u6307\u6325\u5b98\u5728TOP8\u51a0\u519b\u4e89\u9738\u8d5b\u5bf9\u9635\u4e2d\u6253\u5f00\u4e0b\u65b9\u9875\u9762\u540e\u518d\u6267\u884c\u622a\u56fe"' | ConvertFrom-Json
$TextSeasonHelp = '"\u5168\u8d5b\u5b63\u91c7\u96c6\u6d41\u7a0b\u4f1a\u4ece64\u5f3a\u664b\u7ea7\u8d5bGROUP01\u9875\u9762\u5f00\u59cb\uff0c\u4f9d\u6b21\u91c7\u96c6\u6240\u6709GROUP\u768464/32/16\u5f3a\u6570\u636e\uff0c\u968f\u540e\u81ea\u52a8\u8fd4\u56de\u5e76\u8fdb\u5165\u51a0\u519b\u4e89\u9738\u8d5b\u3002"' | ConvertFrom-Json
$TextOcrHelp = ""
$TextOcrDoneMessage = '"\u6218\u540e\u6570\u636e\u8bc6\u522b\u4efb\u52a1\u5df2\u5b8c\u6210\uff0cJSON \u4e0e Excel \u5df2\u5bfc\u51fa\u3002"' | ConvertFrom-Json
$TextOcrNeedDetailed = '"\u9700\u540c\u65f6\u52fe\u9009\u8d5b\u540e\u6570\u636e\uff08\u8be6\u7ec6\uff09"' | ConvertFrom-Json
$TextAutoOcrStartMessage = '"\u6218\u6597\u6570\u636e\u56fe\u50cf\u5df2\u622a\u53d6\u5b8c\u6210\uff0c\u6307\u6325\u5b98\uff0c\u6b63\u5728\u8bc6\u522b\u5e76\u5bfc\u51fa\u6570\u636e\uff0c\u8bf7\u6307\u6325\u5b98\u8010\u5fc3\u7b49\u5f85"' | ConvertFrom-Json
$TextAutoOcrStartTitle = '"\u6b63\u5728\u8bc6\u522b\u6570\u636e"' | ConvertFrom-Json
$TextSettingsHelp = '"\u622a\u56fe\u4e0e\u56fe\u50cf\u8bc6\u522b\u53c2\u6570\u8bbe\u7f6e"' | ConvertFrom-Json
$TextSettingHint = '"\u8bbe\u7f6e\u63d0\u793a"' | ConvertFrom-Json
$TextCustomSingleTip = '"\u8bf7\u5c06 5120x2880 \u6216 16:9 \u9ad8\u6e05 JPG/PNG \u5355\u4eba\u9635\u5bb9\u80cc\u666f\u5e95\u56fe\u653e\u5165 outputs\\\\custom_backgrounds\uff0c\u7a0b\u5e8f\u4f1a\u81ea\u52a8\u4f7f\u7528\u6700\u65b0\u7684\u4e00\u5f20\u3002"' | ConvertFrom-Json
$TextCustomSupportTip = '"\u8bf7\u5c06 5120x2880 \u6216 16:9 \u9ad8\u6e05 JPG/PNG \u5e94\u63f4\u53cc\u65b9\u80cc\u666f\u5e95\u56fe\u653e\u5165 outputs\\\\support_custom_backgrounds\uff0c\u7a0b\u5e8f\u4f1a\u81ea\u52a8\u4f7f\u7528\u6700\u65b0\u7684\u4e00\u5f20\u3002"' | ConvertFrom-Json
$TextCustomGroupTip = '"\u8bf7\u5c06 5120x2880 \u6216 16:9 \u9ad8\u6e05 JPG/PNG GROUP\u9635\u5bb9\u80cc\u666f\u5e95\u56fe\u653e\u5165 outputs\\\\group_custom_backgrounds\uff0c\u7a0b\u5e8f\u4f1a\u81ea\u52a8\u4f7f\u7528\u6700\u65b0\u7684\u4e00\u5f20\u3002"' | ConvertFrom-Json
$TextCustomSeasonTip = '"\u8bf7\u5c06 5120x2880 \u6216 16:9 \u9ad8\u6e05 JPG/PNG \u5168\u8d5b\u5b63\u91c7\u96c6\u80cc\u666f\u5e95\u56fe\u653e\u5165 outputs\\\\group_custom_backgrounds\uff0c\u7a0b\u5e8f\u4f1a\u81ea\u52a8\u4f7f\u7528\u6700\u65b0\u7684\u4e00\u5f20\u3002"' | ConvertFrom-Json

if (-not $Check) {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        $adminMessage = '"\u8bf7\u6307\u6325\u5b98\u53f3\u952e\u8be5\u7a0b\u5e8f\u4ee5\u7ba1\u7406\u5458\u8eab\u4efd\u8fd0\u884c"' | ConvertFrom-Json
        $adminTitle = '"\u9700\u8981\u6307\u6325\u5b98\u6743\u9650"' | ConvertFrom-Json
        [System.Windows.MessageBox]::Show(
            $adminMessage,
            $adminTitle,
            [System.Windows.MessageBoxButton]::OK,
            [System.Windows.MessageBoxImage]::Warning
        ) | Out-Null
        return
    }
}
Add-Type @"
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

public static class NativeWin {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern IntPtr SetFocus(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern IntPtr SetActiveWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint flags);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
[DllImport("user32.dll")] public static extern short GetAsyncKeyState(int vKey);
    [DllImport("user32.dll")] public static extern int GetSystemMetrics(int nIndex);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextLength(IntPtr hWnd);

    public static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
    public static readonly IntPtr HWND_NOTOPMOST = new IntPtr(-2);
    public const int SW_RESTORE = 9;
    public const uint SWP_NOSIZE = 0x0001;
    public const uint SWP_NOMOVE = 0x0002;
    public const uint SWP_SHOWWINDOW = 0x0040;
    public const uint MOD_ALT = 0x0001;
    public const int SM_CXSCREEN = 0;
    public const int SM_CYSCREEN = 1;

    public static bool IsNikkeRunning() {
        return Process.GetProcessesByName("nikke").Length > 0;
    }

    public static IntPtr FindWindowByProcessOrTitle() {
        Process[] processes = Process.GetProcessesByName("nikke");
        foreach (Process p in processes) {
            if (p.MainWindowHandle != IntPtr.Zero) return p.MainWindowHandle;
        }

        IntPtr found = IntPtr.Zero;
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
            if (!IsWindowVisible(hWnd)) return true;
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            foreach (Process p in processes) {
                if ((uint)p.Id == pid) {
                    found = hWnd;
                    return false;
                }
            }

            int len = GetWindowTextLength(hWnd);
            if (len > 0) {
                StringBuilder sb = new StringBuilder(len + 1);
                GetWindowText(hWnd, sb, sb.Capacity);
                string title = sb.ToString();
                if (title.Contains("胜利女神") || title.Contains("新的希望") || title.ToLower().Contains("nikke")) {
                    found = hWnd;
                    return false;
                }
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }

    public static bool FocusGame() {
        IntPtr hWnd = FindWindowByProcessOrTitle();
        if (hWnd == IntPtr.Zero) return false;

        uint targetPid;
        uint targetThread = GetWindowThreadProcessId(hWnd, out targetPid);
        uint currentThread = GetCurrentThreadId();
        IntPtr foreground = GetForegroundWindow();
        uint foregroundPid;
        uint foregroundThread = foreground == IntPtr.Zero ? 0 : GetWindowThreadProcessId(foreground, out foregroundPid);

        if (foregroundThread != 0) AttachThreadInput(currentThread, foregroundThread, true);
        AttachThreadInput(currentThread, targetThread, true);
        try {
            ShowWindow(hWnd, SW_RESTORE);
            SetWindowPos(hWnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW);
            SetWindowPos(hWnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW);
            BringWindowToTop(hWnd);
            SetForegroundWindow(hWnd);
            SetActiveWindow(hWnd);
            SetFocus(hWnd);
        } finally {
            AttachThreadInput(currentThread, targetThread, false);
            if (foregroundThread != 0) AttachThreadInput(currentThread, foregroundThread, false);
        }
        return true;
    }
}
"@

[xml]$Xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="NIKKE Capture" Width="1280" Height="780" MinWidth="1080" MinHeight="690"
        WindowStartupLocation="CenterScreen" Background="#070B13">
  <Window.Resources>
    <SolidColorBrush x:Key="ScrollThumbBrush" Color="#6BDFFF"/>
    <SolidColorBrush x:Key="ScrollTrackBrush" Color="#22324A"/>
    <Style TargetType="{x:Type ScrollBar}">
      <Setter Property="Width" Value="6"/>
      <Setter Property="MinWidth" Value="6"/>
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="{x:Type ScrollBar}">
            <Grid Width="6" Margin="0,10,0,10" Background="Transparent">
              <Border Width="2" HorizontalAlignment="Center" CornerRadius="2" Background="{StaticResource ScrollTrackBrush}" Opacity="0.52"/>
              <Track x:Name="PART_Track" IsDirectionReversed="True">
                <Track.DecreaseRepeatButton>
                  <RepeatButton Command="ScrollBar.PageUpCommand" Opacity="0" IsHitTestVisible="False"/>
                </Track.DecreaseRepeatButton>
                <Track.Thumb>
                  <Thumb>
                    <Thumb.Template>
                      <ControlTemplate TargetType="{x:Type Thumb}">
                        <Border Width="4" HorizontalAlignment="Center" CornerRadius="3" Background="{StaticResource ScrollThumbBrush}"/>
                      </ControlTemplate>
                    </Thumb.Template>
                  </Thumb>
                </Track.Thumb>
                <Track.IncreaseRepeatButton>
                  <RepeatButton Command="ScrollBar.PageDownCommand" Opacity="0" IsHitTestVisible="False"/>
                </Track.IncreaseRepeatButton>
              </Track>
            </Grid>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="PrimaryButton" TargetType="Button">
      <Setter Property="Foreground" Value="#06151F"/>
      <Setter Property="FontFamily" Value="Microsoft YaHei UI"/>
      <Setter Property="FontWeight" Value="Bold"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border CornerRadius="18" BorderThickness="1.2" BorderBrush="#C8F8FF">
              <Border.Background>
                <LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
                  <GradientStop x:Name="PrimaryTop" Color="#7EF2FF" Offset="0"/>
                  <GradientStop x:Name="PrimaryMid" Color="#20C7FF" Offset="0.45"/>
                  <GradientStop x:Name="PrimaryBottom" Color="#1384FF" Offset="1"/>
                </LinearGradientBrush>
              </Border.Background>
              <Grid>
                <Border CornerRadius="16" Margin="2" VerticalAlignment="Top" Height="29" Opacity="0.34" Background="White"/>
                <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
              </Grid>
            </Border>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="DarkButton" TargetType="Button">
      <Setter Property="Foreground" Value="#EAF6FF"/>
      <Setter Property="FontFamily" Value="Microsoft YaHei UI"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border CornerRadius="16" BorderThickness="1" BorderBrush="#5B789A">
              <Border.Background>
                <LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
                  <GradientStop Color="#243750" Offset="0"/>
                  <GradientStop Color="#142236" Offset="1"/>
                </LinearGradientBrush>
              </Border.Background>
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="OcrSlotButton" TargetType="Button">
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Padding" Value="0"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border CornerRadius="8" Background="{TemplateBinding Background}">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="OcrSlotClearButton" TargetType="Button">
      <Setter Property="Width" Value="18"/>
      <Setter Property="Height" Value="18"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Padding" Value="0"/>
      <Setter Property="Background" Value="#E51D242D"/>
      <Setter Property="BorderBrush" Value="#F7FFFFFF"/>
      <Setter Property="Foreground" Value="White"/>
      <Setter Property="FontFamily" Value="Microsoft YaHei UI"/>
      <Setter Property="FontSize" Value="10"/>
      <Setter Property="FontWeight" Value="Bold"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border CornerRadius="9" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="1">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" Margin="0,-1,0,0"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter Property="Background" Value="#F0323A45"/>
              </Trigger>
              <Trigger Property="IsPressed" Value="True">
                <Setter Property="Background" Value="#FF0F151D"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="TinyThemeButton" TargetType="Button">
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Padding" Value="0"/>
      <Setter Property="BorderThickness" Value="1"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border CornerRadius="16" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="1" Background="{TemplateBinding Background}">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="MutedButton" BasedOn="{StaticResource DarkButton}" TargetType="Button">
      <Setter Property="Foreground" Value="#71849B"/>
      <Setter Property="IsEnabled" Value="False"/>
    </Style>
    <Style x:Key="PinkPrimaryButton" TargetType="Button">
      <Setter Property="Foreground" Value="#5A2439"/>
      <Setter Property="FontFamily" Value="Microsoft YaHei UI"/>
      <Setter Property="FontWeight" Value="Bold"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border CornerRadius="18" BorderThickness="1.2" BorderBrush="#FFFFF7FB">
              <Border.Background>
                <LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
                  <GradientStop Color="#FFFFF8FC" Offset="0"/>
                  <GradientStop Color="#FFFFBBD3" Offset="0.48"/>
                  <GradientStop Color="#FFFF8DB9" Offset="1"/>
                </LinearGradientBrush>
              </Border.Background>
              <Grid>
                <Border CornerRadius="16" Margin="2" VerticalAlignment="Top" Height="29" Opacity="0.55" Background="White"/>
                <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
              </Grid>
            </Border>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="PinkDarkButton" TargetType="Button">
      <Setter Property="Foreground" Value="#6D344B"/>
      <Setter Property="FontFamily" Value="Microsoft YaHei UI"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border CornerRadius="16" BorderThickness="1" BorderBrush="#FFFFBCD5">
              <Border.Background>
                <LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
                  <GradientStop Color="#FFFFF8FC" Offset="0"/>
                  <GradientStop Color="#FFFFE1EC" Offset="1"/>
                </LinearGradientBrush>
              </Border.Background>
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="PinkMutedButton" BasedOn="{StaticResource PinkDarkButton}" TargetType="Button">
      <Setter Property="Foreground" Value="#B07A92"/>
      <Setter Property="IsEnabled" Value="False"/>
    </Style>
    <Style x:Key="DarkOptionCheck" TargetType="CheckBox">
      <Setter Property="Foreground" Value="#EAF6FF"/>
      <Setter Property="FontFamily" Value="Microsoft YaHei UI"/>
      <Setter Property="FontSize" Value="12"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="CheckBox">
            <Border x:Name="Pill" CornerRadius="13" BorderThickness="1" BorderBrush="#4C6F90" Background="#40101A2A" Padding="9,5" Margin="3">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsChecked" Value="True">
                <Setter TargetName="Pill" Property="Background" Value="#CC29C7FF"/>
                <Setter TargetName="Pill" Property="BorderBrush" Value="#C8F8FF"/>
                <Setter Property="Foreground" Value="#06151F"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="PinkOptionCheck" TargetType="CheckBox">
      <Setter Property="Foreground" Value="#6D344B"/>
      <Setter Property="FontFamily" Value="Microsoft YaHei UI"/>
      <Setter Property="FontSize" Value="12"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="CheckBox">
            <Border x:Name="Pill" CornerRadius="13" BorderThickness="1" BorderBrush="#FFFFBCD5" Background="#8AFFF8FC" Padding="9,5" Margin="3">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsChecked" Value="True">
                <Setter TargetName="Pill" Property="Background" Value="#FFFFBBD3"/>
                <Setter TargetName="Pill" Property="BorderBrush" Value="#FFFFF7FB"/>
                <Setter Property="Foreground" Value="#5A2439"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="SiteIconButton" TargetType="Button">
      <Setter Property="Width" Value="30"/>
      <Setter Property="Height" Value="30"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Background" Value="#66101A2A"/>
      <Setter Property="BorderBrush" Value="#6BDFFF"/>
      <Setter Property="BorderThickness" Value="1"/>
      <Setter Property="Padding" Value="0"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="RoundButton" Width="{TemplateBinding Width}" Height="{TemplateBinding Height}"
                    CornerRadius="15" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="{TemplateBinding BorderThickness}">
              <Grid Margin="{TemplateBinding Padding}">
                <Grid.Clip>
                  <EllipseGeometry Center="15,15" RadiusX="15" RadiusY="15"/>
                </Grid.Clip>
                <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
              </Grid>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="RoundButton" Property="Background" Value="#CC29C7FF"/>
                <Setter TargetName="RoundButton" Property="BorderBrush" Value="#F7FBFF"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
  </Window.Resources>
  <Grid>
    <Image x:Name="BackgroundImage" Stretch="UniformToFill" RenderTransformOrigin="0.5,0.5"/>
    <Rectangle x:Name="OverlayA" Fill="#AA030712"/>
    <Rectangle x:Name="OverlayB" Fill="#33091423"/>

    <Border x:Name="SubPagePanel" Width="490" HorizontalAlignment="Left" VerticalAlignment="Center" Margin="58,48,0,48"
            CornerRadius="18" BorderBrush="#766BDFFF" BorderThickness="1.1" Visibility="Collapsed">
      <Border.Effect>
        <DropShadowEffect Color="#000000" BlurRadius="24" ShadowDepth="10" Opacity="0.48"/>
      </Border.Effect>
      <Border.Background>
        <LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
          <GradientStop x:Name="SubPanelTop" Color="#E6111C2F" Offset="0"/>
          <GradientStop x:Name="SubPanelBottom" Color="#E407101E" Offset="1"/>
        </LinearGradientBrush>
      </Border.Background>
      <Grid Margin="30">
        <Grid.RowDefinitions>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="*"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>
        <DockPanel Grid.Row="0">
          <Button x:Name="BackButton" DockPanel.Dock="Right" Width="42" Height="32" Content="Back" Style="{StaticResource DarkButton}"/>
          <TextBlock Text="C ARENA" FontFamily="Segoe UI" FontWeight="Bold" FontSize="28" Foreground="#F7FBFF"/>
        </DockPanel>
        <TextBlock x:Name="SubPageHelpText" Grid.Row="1" Text="&#35831;&#25351;&#25381;&#23448;&#20808;&#25171;&#24320;&#20896;&#20891;&#31454;&#25216;&#22330;&#25351;&#23450;&#21442;&#36187;&#32773;&#20449;&#24687;&#65288;&#22914;&#22270;&#65289;&#21518;&#20877;&#25191;&#34892;&#25130;&#22270;" TextWrapping="Wrap"
                   FontFamily="Microsoft YaHei UI" FontSize="14" Foreground="#D7E8F6" Margin="0,14,0,18"/>
        <Border x:Name="ExampleBorder" Grid.Row="2" CornerRadius="18" BorderBrush="#5EDCFF" BorderThickness="1" Background="#66040A14" Padding="10">
          <Image x:Name="ExampleImage" Stretch="Uniform"/>
        </Border>
        <Border x:Name="SettingsPanel" Grid.Row="2" CornerRadius="16" BorderBrush="#5EDCFF" BorderThickness="1" Background="#66040A14" Padding="18" Visibility="Collapsed">
          <StackPanel>
            <TextBlock Text="&#26222;&#36890;&#28857;&#20987;&#21518;&#31561;&#24453;&#33258;&#21160;&#25130;&#22270;&#30340;&#26102;&#38388;&#65288;&#31186;&#65289;" FontFamily="Microsoft YaHei UI" FontSize="13" FontWeight="Bold" Foreground="#D7E8F6" Margin="0,0,0,12"/>
            <Grid>
              <Grid.ColumnDefinitions>
                <ColumnDefinition Width="*"/>
                <ColumnDefinition Width="82"/>
              </Grid.ColumnDefinitions>
              <Slider x:Name="CaptureDelaySlider" Grid.Column="0" Minimum="0.45" Maximum="5" Value="0.80" TickFrequency="0.05" IsSnapToTickEnabled="False" VerticalAlignment="Center" Margin="0,0,14,0"/>
              <TextBox x:Name="CaptureDelayBox" Grid.Column="1" Height="34" Text="0.80" TextAlignment="Center" VerticalContentAlignment="Center"
                       FontFamily="Segoe UI" FontSize="14" Foreground="#F7FBFF" Background="#44101A2A" BorderBrush="#5EDCFF"/>
            </Grid>
            <TextBlock Text="&#40657;&#33394;&#25353;&#38062;&#30340;&#35814;&#32454;&#23545;&#25112;&#25968;&#25454;&#21152;&#36733;&#31561;&#24453;&#26102;&#38388;&#65288;&#31186;&#65289;" FontFamily="Microsoft YaHei UI" FontSize="13" FontWeight="Bold" Foreground="#D7E8F6" Margin="0,22,0,12"/>
            <Grid>
              <Grid.ColumnDefinitions>
                <ColumnDefinition Width="*"/>
                <ColumnDefinition Width="82"/>
              </Grid.ColumnDefinitions>
              <Slider x:Name="DetailDelaySlider" Grid.Column="0" Minimum="0.70" Maximum="5" Value="3.50" TickFrequency="0.05" IsSnapToTickEnabled="False" VerticalAlignment="Center" Margin="0,0,14,0"/>
              <TextBox x:Name="DetailDelayBox" Grid.Column="1" Height="34" Text="3.50" TextAlignment="Center" VerticalContentAlignment="Center"
                       FontFamily="Segoe UI" FontSize="14" Foreground="#F7FBFF" Background="#44101A2A" BorderBrush="#5EDCFF"/>
            </Grid>
            <TextBlock Text="OCR&#36816;&#34892;&#27169;&#24335;" FontFamily="Microsoft YaHei UI" FontSize="13" FontWeight="Bold" Foreground="#D7E8F6" Margin="0,22,0,8"/>
            <WrapPanel HorizontalAlignment="Left">
              <CheckBox x:Name="OcrEcoCheck" Content="&#33410;&#33021; CPU" Style="{StaticResource DarkOptionCheck}" Visibility="Collapsed"/>
              <CheckBox x:Name="OcrBalancedCheck" Content="&#22343;&#34913; CPU" Style="{StaticResource DarkOptionCheck}" Visibility="Collapsed"/>
              <CheckBox x:Name="OcrFullCheck" Content="CPU" IsChecked="True" Style="{StaticResource DarkOptionCheck}"/>
              <CheckBox x:Name="OcrExtremeCheck" Content="&#26497;&#38480; CPU" Style="{StaticResource DarkOptionCheck}" Visibility="Collapsed"/>
              <CheckBox x:Name="OcrGpuCheck" Content="GPU" Style="{StaticResource DarkOptionCheck}" ToolTipService.ShowOnDisabled="True"/>
            </WrapPanel>
            <TextBlock Margin="3,7,0,0" FontFamily="Microsoft YaHei UI" FontSize="11">
              <Hyperlink x:Name="OcrGpuGuideLink" FontWeight="SemiBold" TextDecorations="Underline" ToolTip="&#25171;&#24320; GPU &#27169;&#24335;&#19968;&#38190;&#37197;&#32622;&#25945;&#31243;&#65288;PDF&#65289;">&#25171;&#24320; GPU &#27169;&#24335;&#19968;&#38190;&#37197;&#32622;&#25945;&#31243;&#65288;PDF&#65289;</Hyperlink>
            </TextBlock>
            <TextBlock x:Name="OcrGpuRecommendationText" Text="如果指挥官是NVIDIA中高端显卡，强烈建议用GPU模式进行识图。CPU模式负载较高，且耗时是GPU模式的一倍以上。在CPU模式下长时间的识图任务可能会让您的设备遭到意想不到的意外，如果您坚持使用CPU模式识图，请务必开启过热保护模式。" TextWrapping="Wrap"
                       FontFamily="Microsoft YaHei UI" FontSize="11" FontWeight="Bold" Foreground="#FFD58A" Opacity="1" Margin="3,7,0,0"/>
            <TextBlock Text="GPU&#27169;&#24335;&#38656;&#35201;NVIDIA CUDA&#19982;Paddle GPU&#29615;&#22659;&#65292;&#22914;&#38656;&#20351;&#29992;GPU&#65292;&#35831;&#30830;&#20445;CUDA&#21644;PaddleOCR GPU&#29256;&#26412;&#21487;&#29992;&#12290;" TextWrapping="Wrap"
                       FontFamily="Microsoft YaHei UI" FontSize="10" Foreground="#A9C2D9" Opacity="0.78" Margin="3,5,0,0"/>
            <TextBlock x:Name="OcrPerformanceWarningText" Text="&#24050;&#31227;&#38500;&#24615;&#33021;&#26723;&#20301;&#19982; CPU &#32447;&#31243;&#38480;&#21046;&#65307;&#22914;&#38656;&#20351;&#29992; GPU&#65292;&#35831;&#30830;&#20445; CUDA &#21644; PaddleOCR GPU &#29256;&#26412;&#21487;&#29992;&#12290;" TextWrapping="Wrap"
                       FontFamily="Microsoft YaHei UI" FontSize="10" Foreground="#FFD58A" Opacity="0.94" Margin="3,6,0,0" Visibility="Collapsed"/>
            <TextBlock x:Name="OcrGpuStatusText" Text="GPU &#27169;&#24335;&#38656;&#35201; NVIDIA CUDA &#19982; Paddle GPU &#29615;&#22659;" TextWrapping="Wrap"
                       FontFamily="Microsoft YaHei UI" FontSize="10" Foreground="#A9C2D9" Opacity="0.78" Margin="3,6,0,0" Visibility="Collapsed"/>
            <TextBlock Text="&#24615;&#33021;&#19982;&#28201;&#24230;&#20445;&#25252;" FontFamily="Microsoft YaHei UI" FontSize="13" FontWeight="Bold" Foreground="#D7E8F6" Margin="0,16,0,8"/>
            <WrapPanel HorizontalAlignment="Left">
              <CheckBox x:Name="OcrThermalSafeCheck" Content="&#36807;&#28909;&#20445;&#25252;&#27169;&#24335;&#65288;&#25512;&#33616;&#65289;" IsChecked="True" Style="{StaticResource DarkOptionCheck}"/>
              <CheckBox x:Name="OcrThermalPerformanceCheck" Content="&#24615;&#33021;&#20248;&#20808;&#27169;&#24335;" Style="{StaticResource DarkOptionCheck}" Margin="10,0,0,0"/>
            </WrapPanel>
            <TextBlock x:Name="OcrThermalHintText" Text="&#36807;&#28909;&#20445;&#25252;&#27169;&#24335;&#19981;&#38480;&#21046;&#32447;&#31243;&#65292;&#20165;&#22312;&#27599;&#20010;&#23545;&#23616; block &#32467;&#26463;&#21518;&#30701;&#26242;&#38388;&#27463;&#65292;&#38477;&#20302;&#38271;&#26102;&#38388;&#25345;&#32493;&#28385;&#36733;&#30340;&#27010;&#29575;&#12290;" TextWrapping="Wrap"
                       FontFamily="Microsoft YaHei UI" FontSize="10" Foreground="#A9C2D9" Opacity="0.78" Margin="3,5,0,0"/>
            <CheckBox x:Name="LowMemoryCheck" Content="&#20302;&#20869;&#23384;&#27169;&#24335;" Style="{StaticResource DarkOptionCheck}" HorizontalAlignment="Left" Margin="-3,12,0,0"
                      Visibility="Collapsed" IsEnabled="False" Opacity="0.45" ToolTipService.ShowOnDisabled="True">
              <CheckBox.ToolTip>
                <ToolTip x:Name="LowMemoryTooltip" Placement="Mouse" Background="#F20B1424" BorderBrush="#5EDCFF" BorderThickness="1">
                  <TextBlock x:Name="LowMemoryTooltipText" Text="&#23558;&#29609;&#23478;&#32531;&#23384;&#20889;&#20837;&#30913;&#30424;&#65292;&#20943;&#23569;&#19968;&#38190;&#37319;&#38598;&#26102;&#30340;&#20869;&#23384;&#21344;&#29992;&#65307;&#36895;&#24230;&#21487;&#33021;&#31245;&#24930;&#12290;" Foreground="#F7FBFF" FontFamily="Microsoft YaHei UI" FontSize="12" MaxWidth="300" TextWrapping="Wrap"/>
                </ToolTip>
              </CheckBox.ToolTip>
            </CheckBox>
            <CheckBox x:Name="OcrMediumMemoryCheck" Content="&#20013;&#20869;&#23384;&#27169;&#24335;" Style="{StaticResource DarkOptionCheck}" HorizontalAlignment="Left" Margin="-3,8,0,0"
                      IsEnabled="False" Opacity="0.45" Visibility="Collapsed" ToolTipService.ShowOnDisabled="True">
              <CheckBox.ToolTip>
                <ToolTip x:Name="OcrMediumMemoryTooltip" Placement="Mouse" Background="#F20B1424" BorderBrush="#5EDCFF" BorderThickness="1">
                  <TextBlock x:Name="OcrMediumMemoryTooltipText" Text="&#21246;&#36873;&#21518; OCR &#20351;&#29992; manifest &#23567;&#22359;&#35782;&#21035;&#65292;&#20869;&#23384;&#26356;&#31283;&#20294;&#36895;&#24230;&#36739;&#24930;&#65307;&#19981;&#21246;&#36873;&#26102;&#30452;&#25509;&#35782;&#21035;&#22823;&#22270;&#12290;" Foreground="#F7FBFF" FontFamily="Microsoft YaHei UI" FontSize="12" MaxWidth="330" TextWrapping="Wrap"/>
                </ToolTip>
              </CheckBox.ToolTip>
            </CheckBox>
            <TextBlock x:Name="OcrMediumMemoryDisabledText"
                       Text="&#20013;&#20869;&#23384;&#27169;&#24335;&#65288;manifest &#23567;&#22359; OCR&#65289;&#24050;&#26242;&#26102;&#20572;&#29992;&#65307;&#24403;&#21069;&#40664;&#35748;&#20351;&#29992;&#22823;&#22270;&#30452;&#25509;&#35782;&#21035;&#65292;&#21518;&#32493;&#22914;&#38656;&#38477;&#20302;&#20869;&#23384;&#21344;&#29992;&#21487;&#37325;&#26032;&#21551;&#29992;&#12290;"
                       TextWrapping="Wrap" FontFamily="Microsoft YaHei UI" FontSize="10" Foreground="#A9C2D9" Opacity="0.78" Margin="3,4,0,0" Visibility="Collapsed"/>
          </StackPanel>
        </Border>
        <Button x:Name="ExecuteButton" Grid.Row="3" Height="62" Style="{StaticResource PrimaryButton}" Margin="0,20,0,0">
          <StackPanel>
            <TextBlock Text="&#25191;&#34892;&#25130;&#22270;" FontSize="18" FontWeight="Bold" HorizontalAlignment="Center"/>
          </StackPanel>
        </Button>
        <StackPanel x:Name="GroupExecutePanel" Grid.Row="3" Margin="0,20,0,0" Visibility="Collapsed">
          <Button x:Name="Group64Button" Height="48" Style="{StaticResource DarkButton}" Margin="0,0,0,10">
            <TextBlock Text="&#25191;&#34892;64&#24378;&#35813;&#32452;8&#20154;&#25130;&#22270;" FontSize="15" FontWeight="Bold" HorizontalAlignment="Center"/>
          </Button>
          <Button x:Name="Group32Button" Height="48" Style="{StaticResource DarkButton}" Margin="0,0,0,10">
            <TextBlock Text="&#25191;&#34892;32&#24378;&#35813;&#32452;4&#20154;&#25130;&#22270;" FontSize="15" FontWeight="Bold" HorizontalAlignment="Center"/>
          </Button>
          <Button x:Name="Group16Button" Height="48" Style="{StaticResource DarkButton}">
            <TextBlock Text="&#25191;&#34892;16&#24378;&#35813;&#32452;&#21452;&#20154;&#25130;&#22270;" FontSize="15" FontWeight="Bold" HorizontalAlignment="Center"/>
          </Button>
        </StackPanel>
        <StackPanel x:Name="Top8ExecutePanel" Grid.Row="3" Margin="0,20,0,0" Visibility="Collapsed">
          <Button x:Name="Top8Button8" Height="48" Style="{StaticResource DarkButton}" Margin="0,0,0,10">
            <TextBlock Text="&#25191;&#34892;8&#24378;&#25130;&#22270;" FontSize="15" FontWeight="Bold" HorizontalAlignment="Center"/>
          </Button>
          <Button x:Name="Top8Button4" Height="48" Style="{StaticResource DarkButton}" Margin="0,0,0,10">
            <TextBlock Text="&#25191;&#34892;4&#24378;&#25130;&#22270;" FontSize="15" FontWeight="Bold" HorizontalAlignment="Center"/>
          </Button>
          <Button x:Name="Top8ButtonFinal" Height="48" Style="{StaticResource DarkButton}" Margin="0,0,0,10">
            <TextBlock Text="&#25191;&#34892;&#20896;&#20122;&#20891;&#25130;&#22270;" FontSize="15" FontWeight="Bold" HorizontalAlignment="Center"/>
          </Button>
          <Button x:Name="Top8PyramidButton" Height="62" Style="{StaticResource DarkButton}">
            <StackPanel>
              <TextBlock Text="&#20896;&#20891;&#20105;&#38712;&#36187;&#25112;&#21518;&#25968;&#25454;&#19968;&#22270;&#27969;" FontSize="15" FontWeight="Bold" HorizontalAlignment="Center"/>
              <TextBlock Text="&#20165;&#22312;&#20896;&#20891;&#35806;&#29983;&#21518;&#20351;&#29992;" FontSize="11" Opacity="0.72" HorizontalAlignment="Center" Margin="0,3,0,0"/>
            </StackPanel>
          </Button>
        </StackPanel>
        <StackPanel x:Name="SeasonExecutePanel" Grid.Row="3" Margin="0,20,0,0" Visibility="Collapsed">
          <Button x:Name="SeasonExecuteButton" Height="62" Style="{StaticResource PrimaryButton}">
            <StackPanel>
              <TextBlock Text="&#25191;&#34892;&#19968;&#38190;&#25130;&#22270;" FontSize="18" FontWeight="Bold" HorizontalAlignment="Center"/>
            </StackPanel>
          </Button>
        </StackPanel>
        <StackPanel x:Name="OcrExecutePanel" Grid.Row="3" Margin="0,20,0,0" Visibility="Collapsed">
          <TextBlock Text="选择要识别的全部战斗数据图像，请务必选择带有详细战果页的图像" FontFamily="Microsoft YaHei UI" FontSize="13" FontWeight="Bold" Foreground="#D7E8F6" Margin="4,0,0,8" TextWrapping="Wrap"/>
          <TextBlock x:Name="OcrParameterWarningText" Text="请指挥官在执行识别前务必确认已正确设置相关参数" FontFamily="Microsoft YaHei UI" FontSize="13" FontWeight="Bold" Foreground="#FFE45C" Margin="4,0,0,12" TextWrapping="Wrap"/>
          <Border x:Name="OcrUploadPanel" CornerRadius="12" BorderBrush="#5EDCFF" BorderThickness="1" Background="#66040A14" Padding="14" Margin="0,0,0,12">
            <StackPanel>
              <StackPanel Orientation="Horizontal" HorizontalAlignment="Left" Margin="0,0,0,12">
                <Grid Width="84" Height="84" Margin="0,0,14,0">
                  <Button x:Name="OcrSlotTop8Button" Width="84" Height="84" Style="{StaticResource OcrSlotButton}">
                    <Grid Width="84" Height="84">
                      <Grid.Clip>
                        <RectangleGeometry Rect="0,0,84,84" RadiusX="8" RadiusY="8"/>
                      </Grid.Clip>
                      <Image x:Name="OcrSlotTop8EmptyImage" Stretch="UniformToFill" Opacity="0.96"/>
                      <Image x:Name="OcrSlotTop8Image" Stretch="UniformToFill" Visibility="Collapsed"/>
                    </Grid>
                  </Button>
                  <Button x:Name="OcrSlotTop8ClearButton" Style="{StaticResource OcrSlotClearButton}" HorizontalAlignment="Right" VerticalAlignment="Top" Margin="0,-5,-5,0" Visibility="Collapsed" Content="&#215;"/>
                </Grid>
                <Grid Width="84" Height="84" Margin="0,0,14,0">
                  <Button x:Name="OcrSlotGroup16Button" Width="84" Height="84" Style="{StaticResource OcrSlotButton}">
                    <Grid Width="84" Height="84">
                      <Grid.Clip>
                        <RectangleGeometry Rect="0,0,84,84" RadiusX="8" RadiusY="8"/>
                      </Grid.Clip>
                      <Image x:Name="OcrSlotGroup16EmptyImage" Stretch="UniformToFill" Opacity="0.96"/>
                      <Image x:Name="OcrSlotGroup16Image" Stretch="UniformToFill" Visibility="Collapsed"/>
                    </Grid>
                  </Button>
                  <Button x:Name="OcrSlotGroup16ClearButton" Style="{StaticResource OcrSlotClearButton}" HorizontalAlignment="Right" VerticalAlignment="Top" Margin="0,-5,-5,0" Visibility="Collapsed" Content="&#215;"/>
                </Grid>
                <Grid Width="84" Height="84" Margin="0,0,14,0">
                  <Button x:Name="OcrSlotGroup32Button" Width="84" Height="84" Style="{StaticResource OcrSlotButton}">
                    <Grid Width="84" Height="84">
                      <Grid.Clip>
                        <RectangleGeometry Rect="0,0,84,84" RadiusX="8" RadiusY="8"/>
                      </Grid.Clip>
                      <Image x:Name="OcrSlotGroup32EmptyImage" Stretch="UniformToFill" Opacity="0.96"/>
                      <Image x:Name="OcrSlotGroup32Image" Stretch="UniformToFill" Visibility="Collapsed"/>
                    </Grid>
                  </Button>
                  <Button x:Name="OcrSlotGroup32ClearButton" Style="{StaticResource OcrSlotClearButton}" HorizontalAlignment="Right" VerticalAlignment="Top" Margin="0,-5,-5,0" Visibility="Collapsed" Content="&#215;"/>
                </Grid>
                <Grid Width="84" Height="84">
                  <Button x:Name="OcrSlotGroup64Button" Width="84" Height="84" Style="{StaticResource OcrSlotButton}">
                    <Grid Width="84" Height="84">
                      <Grid.Clip>
                        <RectangleGeometry Rect="0,0,84,84" RadiusX="8" RadiusY="8"/>
                      </Grid.Clip>
                      <Image x:Name="OcrSlotGroup64EmptyImage" Stretch="UniformToFill" Opacity="0.96"/>
                      <Image x:Name="OcrSlotGroup64Image" Stretch="UniformToFill" Visibility="Collapsed"/>
                    </Grid>
                  </Button>
                  <Button x:Name="OcrSlotGroup64ClearButton" Style="{StaticResource OcrSlotClearButton}" HorizontalAlignment="Right" VerticalAlignment="Top" Margin="0,-5,-5,0" Visibility="Collapsed" Content="&#215;"/>
                </Grid>
              </StackPanel>
              <StackPanel HorizontalAlignment="Left">
                <StackPanel Orientation="Horizontal" Margin="0,0,0,4">
                  <TextBlock Text="TOP8-&#20915;&#36187;&#20840;&#37096;&#25112;&#26007;&#25968;&#25454;&#65288;&#35814;&#65289;" FontFamily="Microsoft YaHei UI" FontSize="11" Foreground="#D7E8F6"/>
                  <TextBlock x:Name="OcrStatusTop8" Text="&#26410;&#23601;&#32490;" FontFamily="Microsoft YaHei UI" FontSize="11" FontWeight="Bold" Foreground="#8195AA" Margin="8,0,0,0"/>
                </StackPanel>
                <StackPanel Orientation="Horizontal" Margin="0,0,0,4">
                  <TextBlock Text="16&#36827;8&#20840;&#37096;&#25112;&#26007;&#25968;&#25454;&#65288;&#35814;&#65289;" FontFamily="Microsoft YaHei UI" FontSize="11" Foreground="#D7E8F6"/>
                  <TextBlock x:Name="OcrStatusGroup16" Text="&#26410;&#23601;&#32490;" FontFamily="Microsoft YaHei UI" FontSize="11" FontWeight="Bold" Foreground="#8195AA" Margin="8,0,0,0"/>
                </StackPanel>
                <StackPanel Orientation="Horizontal" Margin="0,0,0,4">
                  <TextBlock Text="32&#36827;16&#20840;&#37096;&#25112;&#26007;&#25968;&#25454;&#65288;&#35814;&#65289;" FontFamily="Microsoft YaHei UI" FontSize="11" Foreground="#D7E8F6"/>
                  <TextBlock x:Name="OcrStatusGroup32" Text="&#26410;&#23601;&#32490;" FontFamily="Microsoft YaHei UI" FontSize="11" FontWeight="Bold" Foreground="#8195AA" Margin="8,0,0,0"/>
                </StackPanel>
                <StackPanel Orientation="Horizontal" Margin="0,0,0,8">
                  <TextBlock Text="64&#36827;32&#20840;&#37096;&#25112;&#26007;&#25968;&#25454;&#65288;&#35814;&#65289;" FontFamily="Microsoft YaHei UI" FontSize="11" Foreground="#D7E8F6"/>
                  <TextBlock x:Name="OcrStatusGroup64" Text="&#26410;&#23601;&#32490;" FontFamily="Microsoft YaHei UI" FontSize="11" FontWeight="Bold" Foreground="#8195AA" Margin="8,0,0,0"/>
                </StackPanel>
                <StackPanel Orientation="Horizontal" Margin="-3,0,0,4">
                  <CheckBox x:Name="OcrPowerCheck" Content="&#22958;&#23020;&#25112;&#21147;" Style="{StaticResource DarkOptionCheck}" HorizontalAlignment="Left" IsChecked="True" Margin="0,0,8,0"/>
                  <CheckBox x:Name="OcrCollectionCheck" Content="&#34255;&#21697;" Style="{StaticResource DarkOptionCheck}" HorizontalAlignment="Left" IsChecked="True" Margin="0,0,8,0"/>
                  <CheckBox x:Name="OcrStatLevelCheck" Content="&#24490;&#29615;&#31561;&#32423;" Style="{StaticResource DarkOptionCheck}" HorizontalAlignment="Left" IsChecked="False"/>
                </StackPanel>
              </StackPanel>
              <TextBlock x:Name="OcrSelectedPathText" Text="-" Visibility="Collapsed"/>
              <CheckBox x:Name="OcrDebugCheck" Content="&#36755;&#20986; debug &#20999;&#20998;&#22270;&#19982;&#26085;&#24535;" Style="{StaticResource DarkOptionCheck}" HorizontalAlignment="Left" Margin="-3,2,0,0" Visibility="Collapsed" IsChecked="False"/>
            </StackPanel>
          </Border>
          <Button x:Name="OcrRunButton" Height="58" Style="{StaticResource PrimaryButton}" Margin="0,0,0,10">
            <StackPanel>
              <TextBlock Text="&#25191;&#34892;&#35782;&#21035;" FontSize="16" FontWeight="Bold" HorizontalAlignment="Center"/>
              <TextBlock Text="1 &#24352;&#22270;&#25353;&#21333;&#22270;&#35782;&#21035;&#65307;4 &#24352;&#22270;&#27719;&#24635;&#35782;&#21035;&#24182;&#23548;&#20986; JSON / Excel" FontSize="10" Opacity="0.72" HorizontalAlignment="Center" Margin="0,3,0,0"/>
            </StackPanel>
          </Button>
          <Button x:Name="NikkeNameListButton" Height="52" Style="{StaticResource DarkButton}" Margin="0,0,0,10">
            <StackPanel>
              <TextBlock Text="&#26356;&#26032;&#22958;&#23020;&#21517;&#21333;" FontSize="14" FontWeight="Bold" HorizontalAlignment="Center"/>
              <TextBlock Text="&#32500;&#25252; OCR &#26657;&#20934;&#21517;&#21333;" FontSize="10" FontWeight="Normal" Opacity="0.7" HorizontalAlignment="Center" Margin="0,3,0,0"/>
            </StackPanel>
          </Button>
        </StackPanel>
        <StackPanel x:Name="FrameOptionsPanel" Grid.Row="4" Margin="0,12,0,0">
          <TextBlock x:Name="FrameOptionsTitleText" Text="&#32972;&#26223;&#29256;&#24213;&#22270;" FontFamily="Microsoft YaHei UI" FontSize="12" FontWeight="Bold" Foreground="#D7E8F6" Margin="4,0,0,6"/>
          <UniformGrid x:Name="FrameOptionsGrid" Columns="4">
            <CheckBox x:Name="MarianFrameCheck" Content="&#29595;&#20029;&#23433;" Style="{StaticResource DarkOptionCheck}"/>
            <CheckBox x:Name="DoroFrameCheck" Content="Doro" Style="{StaticResource DarkOptionCheck}"/>
            <CheckBox x:Name="CinderellaFrameCheck" Content="&#28784;&#22993;&#23064;" Style="{StaticResource DarkOptionCheck}"/>
            <CheckBox x:Name="CustomFrameCheck" Content="&#33258;&#23450;&#20041;" Style="{StaticResource DarkOptionCheck}"
                      ToolTipService.InitialShowDelay="120" ToolTipService.ShowDuration="12000">
              <CheckBox.ToolTip>
                <ToolTip Placement="Mouse" Background="#F4FFF8FC" BorderBrush="#FFFFBCD5" BorderThickness="1">
                  <TextBlock x:Name="CustomFrameTooltipText" Text="&#35831;&#23558; 5120x2880 &#25110; 16:9 &#39640;&#28165; JPG/PNG &#21333;&#20154;&#38453;&#23481;&#32972;&#26223;&#24213;&#22270;&#25918;&#20837; outputs\custom_backgrounds&#65292;&#31243;&#24207;&#20250;&#33258;&#21160;&#20351;&#29992;&#26368;&#26032;&#30340;&#19968;&#24352;&#12290;" Foreground="#6D344B" FontFamily="Microsoft YaHei UI" FontSize="12" Width="260" TextWrapping="Wrap"/>
                </ToolTip>
              </CheckBox.ToolTip>
            </CheckBox>
          </UniformGrid>
          <CheckBox x:Name="SupportStatusCheck" Content="&#24212;&#25588;&#29616;&#29366;" Style="{StaticResource DarkOptionCheck}" Visibility="Collapsed" HorizontalAlignment="Left" Margin="3,8,0,0"/>
          <StackPanel x:Name="GroupPostDataPanel" Visibility="Collapsed" Margin="0,8,0,0">
            <TextBlock Text="&#25112;&#21518;&#25968;&#25454;" FontFamily="Microsoft YaHei UI" FontSize="12" FontWeight="Bold" Foreground="#D7E8F6" Margin="4,0,0,6"/>
            <TextBlock x:Name="GroupPostDataHelpText" Text="&#25903;&#25345;64/32/16&#24378;&#25130;&#22270;&#65292;&#25152;&#26377;GROUP&#27169;&#24335;&#19979;&#21516;&#26679;&#29983;&#25928;" FontFamily="Microsoft YaHei UI" FontSize="11" Foreground="#A9C2D9" Margin="5,0,0,4"/>
            <StackPanel Orientation="Horizontal">
              <CheckBox x:Name="GroupSimpleDataCheck" Content="&#36187;&#21518;&#25968;&#25454;&#65288;&#31616;&#21270;&#65289;" Style="{StaticResource DarkOptionCheck}"/>
              <CheckBox x:Name="GroupDetailedDataCheck" Content="&#36187;&#21518;&#25968;&#25454;&#65288;&#35814;&#32454;&#65289;" Style="{StaticResource DarkOptionCheck}"/>
            </StackPanel>
            <CheckBox x:Name="GroupAllDataCheck" Content="&#25105;&#35201;&#25152;&#26377;GROUP&#30340;&#25968;&#25454;" Style="{StaticResource DarkOptionCheck}" HorizontalAlignment="Left" Margin="3,8,0,0"/>
            <CheckBox x:Name="ExportOcrDataCheck" Content="&#21516;&#26102;&#23548;&#20986;json&#25968;&#25454;&#22359;&#21644;excel&#25968;&#25454;" Style="{StaticResource DarkOptionCheck}"
                      HorizontalAlignment="Left" Margin="3,8,0,0" IsEnabled="False" Opacity="0.45" Visibility="Collapsed"
                      ToolTipService.InitialShowDelay="120" ToolTipService.ShowDuration="12000" ToolTipService.ShowOnDisabled="True">
              <CheckBox.ToolTip>
                <ToolTip x:Name="ExportOcrTooltip" Placement="Mouse" Background="#F20B1424" BorderBrush="#5EDCFF" BorderThickness="1">
                  <StackPanel MaxWidth="360">
                    <TextBlock x:Name="ExportOcrTooltipText" Text="&#38656;&#21516;&#26102;&#21246;&#36873;&#36187;&#21518;&#25968;&#25454;&#65288;&#35814;&#32454;&#65289;" TextDecorations="Strikethrough" Foreground="#F7FBFF" FontFamily="Microsoft YaHei UI" FontSize="12"/>
                    <TextBlock x:Name="ExportOcrTooltipHintText" Text="&#35831;&#25351;&#25381;&#23448;&#33258;&#34892;&#36873;&#25321;&#25112;&#26007;&#25968;&#25454;&#22270;&#20687;&#36827;&#34892;&#35782;&#21035;" Foreground="#F7FBFF" FontFamily="Microsoft YaHei UI" FontSize="12" Margin="0,4,0,0" TextWrapping="Wrap"/>
                  </StackPanel>
                </ToolTip>
              </CheckBox.ToolTip>
            </CheckBox>
          </StackPanel>
        </StackPanel>
      </Grid>
    </Border>

    <StackPanel x:Name="BrandBlock" HorizontalAlignment="Left" VerticalAlignment="Bottom" Margin="62,0,0,118">
      <TextBlock Text="NIKKE" FontFamily="Segoe UI" FontWeight="Bold" FontSize="62" Foreground="#F7FBFF"/>
      <TextBlock Text="Arena Capture Console" FontFamily="Segoe UI Semibold" FontSize="20" Foreground="#64E7FF" Margin="4,-4,0,0"/>
    </StackPanel>

    <StackPanel x:Name="SiteLinksPanel" Orientation="Horizontal" HorizontalAlignment="Left" VerticalAlignment="Bottom" Margin="62,0,0,58">
      <Button x:Name="SiteSkyxmoonButton" Style="{StaticResource SiteIconButton}" Margin="0,0,8,0" ToolTip="NIKKE &#31454;&#25216;&#22330;&#20805;&#33021;&#35745;&#31639;&#22120;">
        <Image x:Name="SiteSkyxmoonIcon" Width="30" Height="30" Stretch="UniformToFill"/>
      </Button>
      <Button x:Name="SiteNikkeTopButton" Style="{StaticResource SiteIconButton}" Margin="0,0,8,0" ToolTip="NIKKE Arena Tools">
        <Image x:Name="SiteNikkeTopIcon" Width="30" Height="30" Stretch="UniformToFill"/>
      </Button>
      <Button x:Name="SiteMerlotJjcButton" Style="{StaticResource SiteIconButton}" Margin="0,0,8,0" ToolTip="NIKKE &#29305;&#27530;&#31454;&#25216;&#22330;&#25915;&#30053;">
        <Image x:Name="SiteMerlotJjcIcon" Width="30" Height="30" Stretch="UniformToFill"/>
      </Button>
      <Button x:Name="SiteGamekeeNikkeButton" Style="{StaticResource SiteIconButton}" Margin="0,0,8,0" ToolTip="妮姬图鉴">
        <Image x:Name="SiteGamekeeNikkeIcon" Width="30" Height="30" Stretch="UniformToFill"/>
      </Button>
      <Button x:Name="SiteBilibiliGuseButton" Style="{StaticResource SiteIconButton}" Margin="0,0,8,0" ToolTip="古色夕阳PVP月刊">
        <Image x:Name="SiteBilibiliGuseIcon" Width="30" Height="30" Stretch="UniformToFill"/>
      </Button>
      <Button x:Name="SiteBilibiliDeen33Button" Style="{StaticResource SiteIconButton}" ToolTip="deen33NIKKE竞技场半月谈">
        <Image x:Name="SiteBilibiliDeen33Icon" Width="30" Height="30" Stretch="UniformToFill"/>
      </Button>
    </StackPanel>

    <TextBlock HorizontalAlignment="Left" VerticalAlignment="Bottom" Margin="62,0,0,28" FontFamily="Segoe UI" FontSize="12" Foreground="#B8D7EA">
      <Hyperlink x:Name="SourceLink">Image source: Pixiewall</Hyperlink>
    </TextBlock>

    <Border x:Name="MainPanel" Width="460" MaxHeight="690" HorizontalAlignment="Right" VerticalAlignment="Center" Margin="0,44,58,44"
            CornerRadius="18" BorderBrush="#766BDFFF" BorderThickness="1.2">
      <Border.Effect>
        <DropShadowEffect Color="#000000" BlurRadius="24" ShadowDepth="10" Opacity="0.55"/>
      </Border.Effect>
      <Border.Background>
        <LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
          <GradientStop x:Name="MainPanelTop" Color="#E6111C2F" Offset="0"/>
          <GradientStop x:Name="MainPanelBottom" Color="#E407101E" Offset="1"/>
        </LinearGradientBrush>
      </Border.Background>
      <ScrollViewer VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled" PanningMode="VerticalOnly" Padding="0" CanContentScroll="False" Margin="0">
      <Grid Margin="28">
        <Grid.RowDefinitions>
          <RowDefinition Height="100"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="*"/>
          <RowDefinition Height="126"/>
        </Grid.RowDefinitions>

        <Grid Grid.Row="0">
          <StackPanel>
            <TextBlock Text="&#25130;&#22270;&#25511;&#21046;&#21488;" FontFamily="Microsoft YaHei UI" FontWeight="Bold" FontSize="30" Foreground="#FAFDFF"/>
            <TextBlock x:Name="MainFullscreenHintText" Text="&#35831;&#25351;&#25381;&#23448;&#23558;NIKKE&#35774;&#32622;&#20026;&#20840;&#23631;&#27169;&#24335;&#21518;&#20877;&#25191;&#34892;&#25130;&#22270;" FontFamily="Microsoft YaHei UI" FontSize="13" FontWeight="Bold" Foreground="#FFE45C" Margin="2,8,0,0"/>
          </StackPanel>
          <StackPanel Orientation="Horizontal" HorizontalAlignment="Right" VerticalAlignment="Top">
            <Button x:Name="MoonThemeButton" Width="34" Height="34" Content="&#9790;" FontSize="19" Foreground="#DDF7FF" Background="#243750" BorderBrush="#80E8FF" Style="{StaticResource TinyThemeButton}" Margin="0,0,8,0"/>
            <Button x:Name="DoroThemeButton" Width="34" Height="34" Background="#FFF2F7" BorderBrush="#FF9AC3" Style="{StaticResource TinyThemeButton}">
              <Image x:Name="DoroImage" Stretch="UniformToFill"/>
            </Button>
          </StackPanel>
        </Grid>

        <Border x:Name="ProcessCard" Grid.Row="1" CornerRadius="16" BorderBrush="#355875" BorderThickness="1" Background="#73101A2A" Padding="16,12" Margin="0,0,0,16">
          <Grid>
            <StackPanel>
              <TextBlock Text="&#32988;&#21033;&#22899;&#31070;&#65306;&#26032;&#30340;&#24076;&#26395;" FontFamily="Microsoft YaHei UI" FontSize="12" Foreground="#A9C2D9"/>
              <TextBlock x:Name="ProcessStatusText" Text="Checking..." FontFamily="Microsoft YaHei UI" FontWeight="Bold" FontSize="18" Foreground="#FFD38A" Margin="0,4,0,0"/>
            </StackPanel>
            <Border HorizontalAlignment="Right" VerticalAlignment="Center" CornerRadius="12" BorderBrush="#FFD38A" BorderThickness="1" Padding="14,6" Background="#1AFFFFFF">
              <StackPanel>
                <TextBlock x:Name="StatusText" Text="&#31354;&#38386;" Foreground="#68F2C2" FontFamily="Microsoft YaHei UI" FontWeight="Bold" FontSize="12" HorizontalAlignment="Center"/>
                <TextBlock x:Name="HotkeyHintText" Text="ALT + 2  &#32039;&#24613;&#32456;&#27490;&#33050;&#26412;&#36816;&#34892;" Foreground="#FFD38A" FontFamily="Microsoft YaHei UI" FontSize="11" FontWeight="SemiBold" Opacity="1" Margin="0,4,0,0" HorizontalAlignment="Center"/>
              </StackPanel>
            </Border>
          </Grid>
        </Border>

        <Button x:Name="SeasonCaptureButton" Grid.Row="3" Height="64" Style="{StaticResource DarkButton}" Margin="0,0,0,16">
          <StackPanel>
            <TextBlock Text="C ARENA&#24403;&#21069;&#36187;&#23395;&#20840;&#37096;&#25112;&#26007;&#22270;&#20687;&#19968;&#38190;&#25130;&#22270;" FontSize="13" FontWeight="Bold" HorizontalAlignment="Center"/>
            <TextBlock x:Name="SeasonButtonHintText" Text="&#20165;&#22312;&#20896;&#20891;&#35806;&#29983;&#21518;&#20351;&#29992;" FontSize="10" FontWeight="SemiBold" Foreground="#FFD58A" HorizontalAlignment="Center" Margin="0,4,0,0"/>
          </StackPanel>
        </Button>

        <Button x:Name="ArenaButton" Grid.Row="4" Height="68" Style="{StaticResource PrimaryButton}" Margin="0,0,0,18">
          <StackPanel>
            <TextBlock Text="C ARENA&#21333;&#20154;&#38453;&#23481;&#25130;&#22270;" FontSize="17" FontWeight="Bold" HorizontalAlignment="Center"/>
            <TextBlock Text="&#25171;&#24320;&#20108;&#32423;&#39029;&#38754;&#24182;&#30830;&#35748;&#25130;&#22270;&#21069;&#32622;&#29366;&#24577;" FontSize="10" FontWeight="Normal" Opacity="0.72" HorizontalAlignment="Center" Margin="0,4,0,0"/>
          </StackPanel>
        </Button>

        <Button x:Name="SupportButton" Grid.Row="5" Height="58" Style="{StaticResource DarkButton}" Margin="0,0,0,16">
          <StackPanel>
            <TextBlock Text="&#24212;&#25588;&#21452;&#26041;&#38453;&#23481;&#25130;&#22270;" FontSize="15" FontWeight="Bold" HorizontalAlignment="Center"/>
            <TextBlock Text="&#24038;&#21491;&#21452;&#26639;&#21512;&#25104;&#24212;&#25588;&#21452;&#26041;&#38271;&#22270;" FontSize="10" FontWeight="Normal" Opacity="0.7" HorizontalAlignment="Center" Margin="0,3,0,0"/>
          </StackPanel>
        </Button>

        <Button x:Name="GroupButton" Grid.Row="6" Height="58" Style="{StaticResource DarkButton}" Margin="0,0,0,16">
          <StackPanel>
            <TextBlock Text="C ARENA &#26187;&#32423;&#36187;" FontSize="14" FontWeight="Bold" HorizontalAlignment="Center"/>
            <TextBlock Text="&#25209;&#37327;&#37319;&#38598;&#26412;&#32452;&#36873;&#25163;&#24182;&#32593;&#26684;&#21512;&#25104;" FontSize="10" FontWeight="Normal" Opacity="0.7" HorizontalAlignment="Center" Margin="0,3,0,0"/>
          </StackPanel>
        </Button>

        <Button x:Name="Top8Button" Grid.Row="7" Height="58" Style="{StaticResource DarkButton}" Margin="0,0,0,16">
          <StackPanel>
            <TextBlock Text="C ARENA TOP8&#20896;&#20891;&#20105;&#38712;&#36187;" FontSize="14" FontWeight="Bold" HorizontalAlignment="Center"/>
            <TextBlock Text="TOP8/4&#24378;/&#20896;&#20122;&#20891;&#23545;&#38453;&#25130;&#22270;&#20837;&#21475;" FontSize="10" FontWeight="Normal" Opacity="0.7" HorizontalAlignment="Center" Margin="0,3,0,0"/>
          </StackPanel>
        </Button>

        <StackPanel Grid.Row="8">
          <Button x:Name="PostDataOcrButton" Height="58" Style="{StaticResource DarkButton}" Margin="0,0,0,16">
            <StackPanel>
              <TextBlock Text="&#25112;&#26007;&#22270;&#20687;&#35782;&#21035;" FontSize="14" FontWeight="Bold" HorizontalAlignment="Center"/>
              <TextBlock Text="&#23548;&#20986;json&#25968;&#25454;&#22359;&#19982;excel&#29992;&#20110;&#25968;&#25454;&#20998;&#26512;" FontSize="10" FontWeight="Normal" Opacity="0.7" HorizontalAlignment="Center" Margin="0,3,0,0"/>
            </StackPanel>
          </Button>
        </StackPanel>

        <Button x:Name="FolderButton" Grid.Row="9" Height="52" Style="{StaticResource DarkButton}" Margin="0,0,0,28">
          <StackPanel>
            <TextBlock Text="&#25171;&#24320;&#25130;&#22270;&#25991;&#20214;&#22841;" FontSize="14" HorizontalAlignment="Center"/>
            <TextBlock Text="&#26597;&#30475;&#29983;&#25104;&#30340; PNG &#38271;&#22270;" FontSize="10" Opacity="0.7" HorizontalAlignment="Center" Margin="0,3,0,0"/>
          </StackPanel>
        </Button>

        <Button x:Name="SettingsButton" Grid.Row="2" Height="48" Style="{StaticResource DarkButton}" Margin="0,0,0,16">
          <TextBlock Text="&#25130;&#22270;&#19982;&#22270;&#20687;&#35782;&#21035;&#21442;&#25968;&#35774;&#32622;" FontSize="14" FontWeight="Bold" HorizontalAlignment="Center"/>
        </Button>

        <StackPanel Grid.Row="10">
          <TextBlock Text="&#39044;&#30041;&#21151;&#33021;" FontFamily="Microsoft YaHei UI" FontWeight="Bold" FontSize="12" Foreground="#7EE6FF" Margin="2,0,0,10"/>
          <Button x:Name="ReservedButton1" Height="42" Style="{StaticResource MutedButton}" Content="&#29305;&#27530;&#31454;&#25216;&#22330;&#20449;&#24687;" Margin="0,0,0,10"/>
          <Button x:Name="ReservedButton2" Height="42" Style="{StaticResource MutedButton}" Content="&#29609;&#23478;&#26723;&#26696;&#25209;&#37327;&#25130;&#22270;" Margin="0,0,0,10"/>
        </StackPanel>

        <StackPanel Grid.Row="11" VerticalAlignment="Bottom">
          <TextBlock Text="&#36816;&#34892;&#26085;&#24535;" FontFamily="Microsoft YaHei UI" FontWeight="Bold" FontSize="12" Foreground="#E8F7FF" Margin="2,0,0,8"/>
          <Border x:Name="LogCard" CornerRadius="16" BorderBrush="#365875" BorderThickness="1" Background="#B006101E" Padding="16,12">
            <TextBlock x:Name="LogText" Text="Idle." FontFamily="Consolas" FontSize="12" Foreground="#BBD0E1" TextWrapping="Wrap"/>
          </Border>
        </StackPanel>
      </Grid>
      </ScrollViewer>
    </Border>
  </Grid>
</Window>
"@

$Reader = New-Object System.Xml.XmlNodeReader $Xaml
$Window = [Windows.Markup.XamlReader]::Load($Reader)

$BackgroundImage = $Window.FindName("BackgroundImage")
$ExampleImage = $Window.FindName("ExampleImage")
$DoroImage = $Window.FindName("DoroImage")
$ArenaButton = $Window.FindName("ArenaButton")
$SupportButton = $Window.FindName("SupportButton")
$GroupButton = $Window.FindName("GroupButton")
$Top8Button = $Window.FindName("Top8Button")
$SeasonCaptureButton = $Window.FindName("SeasonCaptureButton")
$SeasonButtonHintText = $Window.FindName("SeasonButtonHintText")
$NikkeNameListButton = $Window.FindName("NikkeNameListButton")
$PostDataOcrButton = $Window.FindName("PostDataOcrButton")
$ExecuteButton = $Window.FindName("ExecuteButton")
$GroupExecutePanel = $Window.FindName("GroupExecutePanel")
$Group64Button = $Window.FindName("Group64Button")
$Group32Button = $Window.FindName("Group32Button")
$Group16Button = $Window.FindName("Group16Button")
$Top8ExecutePanel = $Window.FindName("Top8ExecutePanel")
$Top8Button8 = $Window.FindName("Top8Button8")
$Top8Button4 = $Window.FindName("Top8Button4")
$Top8ButtonFinal = $Window.FindName("Top8ButtonFinal")
$Top8PyramidButton = $Window.FindName("Top8PyramidButton")
$SeasonExecutePanel = $Window.FindName("SeasonExecutePanel")
$SeasonExecuteButton = $Window.FindName("SeasonExecuteButton")
$OcrExecutePanel = $Window.FindName("OcrExecutePanel")
$OcrParameterWarningText = $Window.FindName("OcrParameterWarningText")
$OcrSelectedPathText = $Window.FindName("OcrSelectedPathText")
$OcrDebugCheck = $Window.FindName("OcrDebugCheck")
$OcrSelectFileButton = $Window.FindName("OcrSelectFileButton")
$OcrExampleButton = $Window.FindName("OcrExampleButton")
$OcrRunButton = $Window.FindName("OcrRunButton")
$OcrOpenFolderButton = $Window.FindName("OcrOpenFolderButton")
$OcrUploadPanel = $Window.FindName("OcrUploadPanel")
$OcrSlotTop8Button = $Window.FindName("OcrSlotTop8Button")
$OcrSlotGroup16Button = $Window.FindName("OcrSlotGroup16Button")
$OcrSlotGroup32Button = $Window.FindName("OcrSlotGroup32Button")
$OcrSlotGroup64Button = $Window.FindName("OcrSlotGroup64Button")
$OcrSlotTop8Image = $Window.FindName("OcrSlotTop8Image")
$OcrSlotGroup16Image = $Window.FindName("OcrSlotGroup16Image")
$OcrSlotGroup32Image = $Window.FindName("OcrSlotGroup32Image")
$OcrSlotGroup64Image = $Window.FindName("OcrSlotGroup64Image")
$OcrSlotTop8EmptyImage = $Window.FindName("OcrSlotTop8EmptyImage")
$OcrSlotGroup16EmptyImage = $Window.FindName("OcrSlotGroup16EmptyImage")
$OcrSlotGroup32EmptyImage = $Window.FindName("OcrSlotGroup32EmptyImage")
$OcrSlotGroup64EmptyImage = $Window.FindName("OcrSlotGroup64EmptyImage")
$OcrSlotTop8ClearButton = $Window.FindName("OcrSlotTop8ClearButton")
$OcrSlotGroup16ClearButton = $Window.FindName("OcrSlotGroup16ClearButton")
$OcrSlotGroup32ClearButton = $Window.FindName("OcrSlotGroup32ClearButton")
$OcrSlotGroup64ClearButton = $Window.FindName("OcrSlotGroup64ClearButton")
$OcrSlotTop8Plus = $Window.FindName("OcrSlotTop8Plus")
$OcrSlotGroup16Plus = $Window.FindName("OcrSlotGroup16Plus")
$OcrSlotGroup32Plus = $Window.FindName("OcrSlotGroup32Plus")
$OcrSlotGroup64Plus = $Window.FindName("OcrSlotGroup64Plus")
$OcrStatusTop8 = $Window.FindName("OcrStatusTop8")
$OcrStatusGroup16 = $Window.FindName("OcrStatusGroup16")
$OcrStatusGroup32 = $Window.FindName("OcrStatusGroup32")
$OcrStatusGroup64 = $Window.FindName("OcrStatusGroup64")
$BackButton = $Window.FindName("BackButton")
$FolderButton = $Window.FindName("FolderButton")
$SettingsButton = $Window.FindName("SettingsButton")
$MoonThemeButton = $Window.FindName("MoonThemeButton")
$DoroThemeButton = $Window.FindName("DoroThemeButton")
$SubPagePanel = $Window.FindName("SubPagePanel")
$SubPageHelpText = $Window.FindName("SubPageHelpText")
$BrandBlock = $Window.FindName("BrandBlock")
$MainFullscreenHintText = $Window.FindName("MainFullscreenHintText")
$StatusText = $Window.FindName("StatusText")
$HotkeyHintText = $Window.FindName("HotkeyHintText")
$ProcessStatusText = $Window.FindName("ProcessStatusText")
$LogText = $Window.FindName("LogText")
$OverlayA = $Window.FindName("OverlayA")
$OverlayB = $Window.FindName("OverlayB")
$MainPanel = $Window.FindName("MainPanel")
$ProcessCard = $Window.FindName("ProcessCard")
$LogCard = $Window.FindName("LogCard")
$ReservedButton1 = $Window.FindName("ReservedButton1")
$ReservedButton2 = $Window.FindName("ReservedButton2")
$SourceLink = $Window.FindName("SourceLink")
$SiteLinksPanel = $Window.FindName("SiteLinksPanel")
$SiteSkyxmoonButton = $Window.FindName("SiteSkyxmoonButton")
$SiteNikkeTopButton = $Window.FindName("SiteNikkeTopButton")
$SiteMerlotJjcButton = $Window.FindName("SiteMerlotJjcButton")
$SiteGamekeeNikkeButton = $Window.FindName("SiteGamekeeNikkeButton")
$SiteBilibiliGuseButton = $Window.FindName("SiteBilibiliGuseButton")
$SiteBilibiliDeen33Button = $Window.FindName("SiteBilibiliDeen33Button")
$SiteSkyxmoonIcon = $Window.FindName("SiteSkyxmoonIcon")
$SiteNikkeTopIcon = $Window.FindName("SiteNikkeTopIcon")
$SiteMerlotJjcIcon = $Window.FindName("SiteMerlotJjcIcon")
$SiteGamekeeNikkeIcon = $Window.FindName("SiteGamekeeNikkeIcon")
$SiteBilibiliGuseIcon = $Window.FindName("SiteBilibiliGuseIcon")
$SiteBilibiliDeen33Icon = $Window.FindName("SiteBilibiliDeen33Icon")
$ExampleBorder = $Window.FindName("ExampleBorder")
$SettingsPanel = $Window.FindName("SettingsPanel")
$FrameOptionsPanel = $Window.FindName("FrameOptionsPanel")
$FrameOptionsTitleText = $Window.FindName("FrameOptionsTitleText")
$FrameOptionsGrid = $Window.FindName("FrameOptionsGrid")
$CaptureDelaySlider = $Window.FindName("CaptureDelaySlider")
$CaptureDelayBox = $Window.FindName("CaptureDelayBox")
$DetailDelaySlider = $Window.FindName("DetailDelaySlider")
$DetailDelayBox = $Window.FindName("DetailDelayBox")
$OcrEcoCheck = $Window.FindName("OcrEcoCheck")
$OcrBalancedCheck = $Window.FindName("OcrBalancedCheck")
$OcrFullCheck = $Window.FindName("OcrFullCheck")
$OcrExtremeCheck = $Window.FindName("OcrExtremeCheck")
$OcrGpuCheck = $Window.FindName("OcrGpuCheck")
$OcrGpuGuideLink = $Window.FindName("OcrGpuGuideLink")
$OcrGpuStatusText = $Window.FindName("OcrGpuStatusText")
$OcrPerformanceWarningText = $Window.FindName("OcrPerformanceWarningText")
$OcrGpuRecommendationText = $Window.FindName("OcrGpuRecommendationText")
$OcrThermalSafeCheck = $Window.FindName("OcrThermalSafeCheck")
$OcrThermalPerformanceCheck = $Window.FindName("OcrThermalPerformanceCheck")
$OcrThermalHintText = $Window.FindName("OcrThermalHintText")
$LowMemoryCheck = $Window.FindName("LowMemoryCheck")
$LowMemoryTooltip = $Window.FindName("LowMemoryTooltip")
$LowMemoryTooltipText = $Window.FindName("LowMemoryTooltipText")
$OcrMediumMemoryCheck = $Window.FindName("OcrMediumMemoryCheck")
$OcrMediumMemoryTooltip = $Window.FindName("OcrMediumMemoryTooltip")
$OcrMediumMemoryTooltipText = $Window.FindName("OcrMediumMemoryTooltipText")
$OcrMediumMemoryDisabledText = $Window.FindName("OcrMediumMemoryDisabledText")
$MarianFrameCheck = $Window.FindName("MarianFrameCheck")
$DoroFrameCheck = $Window.FindName("DoroFrameCheck")
$CinderellaFrameCheck = $Window.FindName("CinderellaFrameCheck")
$CustomFrameCheck = $Window.FindName("CustomFrameCheck")
$CustomFrameTooltipText = $Window.FindName("CustomFrameTooltipText")
$SupportStatusCheck = $Window.FindName("SupportStatusCheck")
$GroupPostDataPanel = $Window.FindName("GroupPostDataPanel")
$GroupPostDataHelpText = $Window.FindName("GroupPostDataHelpText")
$GroupSimpleDataCheck = $Window.FindName("GroupSimpleDataCheck")
$GroupDetailedDataCheck = $Window.FindName("GroupDetailedDataCheck")
$GroupAllDataCheck = $Window.FindName("GroupAllDataCheck")
$ExportOcrDataCheck = $Window.FindName("ExportOcrDataCheck")
$ExportOcrTooltip = $Window.FindName("ExportOcrTooltip")
$ExportOcrTooltipText = $Window.FindName("ExportOcrTooltipText")
$ExportOcrTooltipHintText = $Window.FindName("ExportOcrTooltipHintText")
$OcrPowerCheck = $Window.FindName("OcrPowerCheck")
$OcrCollectionCheck = $Window.FindName("OcrCollectionCheck")
$OcrStatLevelCheck = $Window.FindName("OcrStatLevelCheck")

function New-Bitmap($Path) {
    if (-not (Test-Path $Path)) { return $null }
    $bitmap = New-Object Windows.Media.Imaging.BitmapImage
    $bitmap.BeginInit()
    $bitmap.UriSource = [Uri]::new($Path)
    $bitmap.CacheOption = [Windows.Media.Imaging.BitmapCacheOption]::OnLoad
    $bitmap.EndInit()
    return $bitmap
}

function Set-SiteIconSource($Image, $Path) {
    if ($Image -and (Test-Path $Path)) {
        $Image.Source = New-Bitmap $Path
    }
}

Set-SiteIconSource $SiteSkyxmoonIcon $SiteSkyxmoonIconPath
Set-SiteIconSource $SiteNikkeTopIcon $SiteNikkeTopIconPath
Set-SiteIconSource $SiteMerlotJjcIcon $SiteMerlotJjcIconPath
Set-SiteIconSource $SiteGamekeeNikkeIcon $SiteGamekeeNikkeIconPath
Set-SiteIconSource $SiteBilibiliGuseIcon $SiteBilibiliGuseIconPath
Set-SiteIconSource $SiteBilibiliDeen33Icon $SiteBilibiliDeen33IconPath
if (Test-Path $AppIconPath) {
    $Window.Icon = New-Bitmap $AppIconPath
}

function Set-Brush($Element, $Property, $Color) {
    if (-not $Element) { return }
    $Element.$Property = [Windows.Media.BrushConverter]::new().ConvertFromString($Color)
}

function Set-Style($Element, $StyleName) {
    if (-not $Element) { return }
    $Element.Style = $Window.Resources[$StyleName]
}

function Resolve-ImageVariant($Path) {
    if (Test-Path $Path) { return $Path }

    $dir = Split-Path -Parent $Path
    $baseName = [IO.Path]::GetFileNameWithoutExtension($Path)
    foreach ($extension in @(".png", ".jpg", ".jpeg")) {
        $candidate = Join-Path $dir ($baseName + $extension)
        if (Test-Path $candidate) { return $candidate }
    }

    return $Path
}

function Resolve-OptionalImage($Primary, $Fallback) {
    if (Test-Path $Primary) { return $Primary }
    return $Fallback
}

function Get-OutputDateFolder {
    $folder = Join-Path $OutputRoot (Get-Date -Format "yyyy-MM-dd")
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
    return $folder
}

function Get-NikkeNameData {
    if (-not (Test-Path $NikkeNameListPath)) {
        return [pscustomobject]@{
            Source = "manual"
            Names = @()
            CollectionNames = @()
            ProtectedNames = @()
            ProtectedCollectionNames = @()
        }
    }

    try {
        $raw = Get-Content -LiteralPath $NikkeNameListPath -Raw -Encoding UTF8
        if (-not $raw.Trim()) { throw "empty name list" }
        $data = $raw | ConvertFrom-Json
        $source = "manual"
        $rawNames = @()
        if ($data.PSObject.Properties.Name -contains "names") {
            if ($data.source) { $source = [string]$data.source }
            if ($source -like "*gamekee.com*") { $source = "local" }
            $rawNames = @($data.names)
            if ($data.PSObject.Properties.Name -contains "collection_names") {
                $rawCollectionNames = @($data.collection_names)
            } else {
                $rawCollectionNames = @()
            }
            if ($data.PSObject.Properties.Name -contains "protected_names") {
                $rawProtectedNames = @($data.protected_names)
            } else {
                $rawProtectedNames = @($data.names)
            }
            if ($data.PSObject.Properties.Name -contains "protected_collection_names") {
                $rawProtectedCollectionNames = @($data.protected_collection_names)
            } else {
                $rawProtectedCollectionNames = @($rawCollectionNames)
            }
        } else {
            $rawNames = @($data)
            $rawCollectionNames = @()
            $rawProtectedNames = @($data)
            $rawProtectedCollectionNames = @()
        }
        $names = @($rawNames | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ })
        $collectionNames = @($rawCollectionNames | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ })
        $protectedNames = @($rawProtectedNames | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ })
        $protectedCollectionNames = @($rawProtectedCollectionNames | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ })
        return [pscustomobject]@{
            Source = $source
            Names = $names
            CollectionNames = $collectionNames
            ProtectedNames = $protectedNames
            ProtectedCollectionNames = $protectedCollectionNames
        }
    } catch {
        return [pscustomobject]@{
            Source = "manual"
            Names = @()
            CollectionNames = @()
            ProtectedNames = @()
            ProtectedCollectionNames = @()
        }
    }
}

function Normalize-NikkeNameForStorage($Name) {
    return (([string]$Name).Trim()).Replace(":", "：")
}

function Test-NikkeSpecialName($Name) {
    return ([string]$Name) -match "[:：︓﹕∶꞉ꓽ]"
}

function Save-NikkeNameData($Names, $Source, $CollectionNames = @(), $ProtectedNames = @(), $ProtectedCollectionNames = @()) {
    $unique = New-Object System.Collections.Generic.List[string]
    foreach ($name in $Names) {
        $trimmed = Normalize-NikkeNameForStorage $name
        if ($trimmed -and -not $unique.Contains($trimmed)) {
            [void]$unique.Add($trimmed)
        }
    }

    $collectionSet = New-Object System.Collections.Generic.HashSet[string]
    foreach ($name in $CollectionNames) {
        $trimmed = Normalize-NikkeNameForStorage $name
        if ($trimmed -and $unique.Contains($trimmed)) {
            [void]$collectionSet.Add($trimmed)
        }
    }

    $protectedSet = New-Object System.Collections.Generic.HashSet[string]
    foreach ($name in $ProtectedNames) {
        $trimmed = Normalize-NikkeNameForStorage $name
        if ($trimmed -and $unique.Contains($trimmed)) {
            [void]$protectedSet.Add($trimmed)
        }
    }
    $protectedNamesForPayload = @($unique.ToArray() | Where-Object { $protectedSet.Contains($_) })

    $protectedCollectionSet = New-Object System.Collections.Generic.HashSet[string]
    foreach ($name in $ProtectedCollectionNames) {
        $trimmed = Normalize-NikkeNameForStorage $name
        if ($trimmed -and $unique.Contains($trimmed)) {
            [void]$protectedCollectionSet.Add($trimmed)
            [void]$collectionSet.Add($trimmed)
        }
    }
    $collectionNamesForPayload = @($unique.ToArray() | Where-Object { $collectionSet.Contains($_) })
    $protectedCollectionNamesForPayload = @($unique.ToArray() | Where-Object { $protectedCollectionSet.Contains($_) })

    if ([string]::IsNullOrWhiteSpace($Source)) { $Source = "manual" }
    $specialNames = @($unique.ToArray() | Where-Object { Test-NikkeSpecialName $_ })
    $payload = [ordered]@{
        source = $Source
        updated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        count = $unique.Count
        names = @($unique.ToArray())
        special_count = $specialNames.Count
        special_names = @($specialNames)
        collection_count = $collectionNamesForPayload.Count
        collection_names = @($collectionNamesForPayload)
        protected_count = $protectedNamesForPayload.Count
        protected_names = @($protectedNamesForPayload)
        protected_collection_count = $protectedCollectionNamesForPayload.Count
        protected_collection_names = @($protectedCollectionNamesForPayload)
    }

    $folder = Split-Path -Parent $NikkeNameListPath
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
    $json = $payload | ConvertTo-Json -Depth 6
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($NikkeNameListPath, ($json + [Environment]::NewLine), $utf8NoBom)
}

function Show-NikkeNameManager {
    $data = Get-NikkeNameData
    $collectionSet = New-Object System.Collections.Generic.HashSet[string]
    foreach ($name in $data.CollectionNames) {
        $trimmed = Normalize-NikkeNameForStorage $name
        if ($trimmed) { [void]$collectionSet.Add($trimmed) }
    }
    $protectedSet = New-Object System.Collections.Generic.HashSet[string]
    foreach ($name in $data.ProtectedNames) {
        $trimmed = Normalize-NikkeNameForStorage $name
        if ($trimmed) { [void]$protectedSet.Add($trimmed) }
    }
    $protectedCollectionSet = New-Object System.Collections.Generic.HashSet[string]
    foreach ($name in $data.ProtectedCollectionNames) {
        $trimmed = Normalize-NikkeNameForStorage $name
        if ($trimmed) { [void]$protectedCollectionSet.Add($trimmed) }
    }
    $allRows = New-Object "System.Collections.ObjectModel.ObservableCollection[object]"
    $seenNames = New-Object System.Collections.Generic.HashSet[string]
    foreach ($name in $data.Names) {
        $trimmed = Normalize-NikkeNameForStorage $name
        if ($trimmed -and -not $seenNames.Contains($trimmed)) {
            [void]$seenNames.Add($trimmed)
            [void]$allRows.Add([pscustomobject]@{
                Name = $trimmed
                HasCollection = ($collectionSet.Contains($trimmed) -or $protectedCollectionSet.Contains($trimmed))
                IsProtected = $protectedSet.Contains($trimmed)
                IsCollectionProtected = $protectedCollectionSet.Contains($trimmed)
                CanToggleCollection = -not $protectedCollectionSet.Contains($trimmed)
                CanDelete = -not $protectedSet.Contains($trimmed)
            })
        }
    }

    $managerXaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="更新妮姬名单"
        Width="620" Height="720"
        WindowStartupLocation="CenterOwner"
        ResizeMode="CanResize"
        FontFamily="Microsoft YaHei UI"
        Background="Transparent">
  <Window.Resources>
    <BooleanToVisibilityConverter x:Key="BoolToVisibilityConverter"/>
    <SolidColorBrush x:Key="NameGridHeaderBrush" Color="#122338"/>
    <SolidColorBrush x:Key="NameGridHeaderTextBrush" Color="#DDF7FBFF"/>
    <SolidColorBrush x:Key="NameGridBorderBrush" Color="#5EDCFF"/>
    <SolidColorBrush x:Key="NameGridSelectionBrush" Color="#263F5F"/>
    <SolidColorBrush x:Key="NameGridSelectionTextBrush" Color="#F7FBFF"/>
    <SolidColorBrush x:Key="NameGridScrollThumbBrush" Color="#6BDFFF"/>
    <SolidColorBrush x:Key="NameGridScrollTrackBrush" Color="#22324A"/>

    <Style TargetType="{x:Type ScrollBar}">
      <Setter Property="Width" Value="6"/>
      <Setter Property="MinWidth" Value="6"/>
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="{x:Type ScrollBar}">
            <Grid Width="6" Margin="0,10,0,10" Background="Transparent">
              <Border Width="2" HorizontalAlignment="Center" CornerRadius="2" Background="{DynamicResource NameGridScrollTrackBrush}" Opacity="0.52"/>
              <Track x:Name="PART_Track" IsDirectionReversed="True">
                <Track.DecreaseRepeatButton>
                  <RepeatButton Command="ScrollBar.PageUpCommand" Opacity="0" IsHitTestVisible="False"/>
                </Track.DecreaseRepeatButton>
                <Track.Thumb>
                  <Thumb>
                    <Thumb.Template>
                      <ControlTemplate TargetType="{x:Type Thumb}">
                        <Border Width="4" HorizontalAlignment="Center" CornerRadius="3" Background="{DynamicResource NameGridScrollThumbBrush}"/>
                      </ControlTemplate>
                    </Thumb.Template>
                  </Thumb>
                </Track.Thumb>
                <Track.IncreaseRepeatButton>
                  <RepeatButton Command="ScrollBar.PageDownCommand" Opacity="0" IsHitTestVisible="False"/>
                </Track.IncreaseRepeatButton>
              </Track>
            </Grid>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="NameGridHeaderStyle" TargetType="{x:Type DataGridColumnHeader}">
      <Setter Property="Height" Value="30"/>
      <Setter Property="Padding" Value="8,0"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="Background" Value="{DynamicResource NameGridHeaderBrush}"/>
      <Setter Property="Foreground" Value="{DynamicResource NameGridHeaderTextBrush}"/>
      <Setter Property="BorderBrush" Value="{DynamicResource NameGridBorderBrush}"/>
      <Setter Property="BorderThickness" Value="0,0,1,1"/>
      <Setter Property="HorizontalContentAlignment" Value="Left"/>
      <Setter Property="VerticalContentAlignment" Value="Center"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="{x:Type DataGridColumnHeader}">
            <Border Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="{TemplateBinding BorderThickness}" Padding="{TemplateBinding Padding}">
              <Grid>
                <ContentPresenter Margin="0,0,14,0" HorizontalAlignment="{TemplateBinding HorizontalContentAlignment}" VerticalAlignment="{TemplateBinding VerticalContentAlignment}" SnapsToDevicePixels="{TemplateBinding SnapsToDevicePixels}"/>
                <Path x:Name="SortArrow" Width="8" Height="5" HorizontalAlignment="Right" VerticalAlignment="Center" Fill="{DynamicResource NameGridHeaderTextBrush}" Stretch="Fill" Opacity="0.45" Data="M 0 5 L 4 0 L 8 5 Z"/>
              </Grid>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="SortDirection" Value="Ascending">
                <Setter TargetName="SortArrow" Property="Opacity" Value="1"/>
                <Setter TargetName="SortArrow" Property="RenderTransform">
                  <Setter.Value>
                    <RotateTransform Angle="0" CenterX="4" CenterY="2.5"/>
                  </Setter.Value>
                </Setter>
              </Trigger>
              <Trigger Property="SortDirection" Value="Descending">
                <Setter TargetName="SortArrow" Property="Opacity" Value="1"/>
                <Setter TargetName="SortArrow" Property="RenderTransform">
                  <Setter.Value>
                    <RotateTransform Angle="180" CenterX="4" CenterY="2.5"/>
                  </Setter.Value>
                </Setter>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="NameGridCellStyle" TargetType="{x:Type DataGridCell}">
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="BorderBrush" Value="Transparent"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="FocusVisualStyle" Value="{x:Null}"/>
      <Style.Triggers>
        <Trigger Property="IsSelected" Value="True">
          <Setter Property="Background" Value="{DynamicResource NameGridSelectionBrush}"/>
          <Setter Property="Foreground" Value="{DynamicResource NameGridSelectionTextBrush}"/>
        </Trigger>
      </Style.Triggers>
    </Style>

    <Style x:Key="NameGridCollectionCheckBoxStyle" TargetType="{x:Type CheckBox}">
      <Setter Property="HorizontalAlignment" Value="Center"/>
      <Setter Property="VerticalAlignment" Value="Center"/>
      <Setter Property="IsEnabled" Value="{Binding CanToggleCollection}"/>
      <Setter Property="ToolTip" Value="珍藏品"/>
      <Style.Triggers>
        <Trigger Property="IsEnabled" Value="False">
          <Setter Property="Opacity" Value="0.82"/>
          <Setter Property="ToolTip" Value="原始珍藏品名单，不可取消勾选"/>
        </Trigger>
      </Style.Triggers>
    </Style>

    <Style x:Key="NameGridDeleteButtonStyle" TargetType="{x:Type Button}">
      <Setter Property="Width" Value="18"/>
      <Setter Property="Height" Value="18"/>
      <Setter Property="Padding" Value="0"/>
      <Setter Property="Margin" Value="6,0,0,0"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Background" Value="#E51D242D"/>
      <Setter Property="BorderBrush" Value="#F7FFFFFF"/>
      <Setter Property="Foreground" Value="White"/>
      <Setter Property="ToolTip" Value="删除该自定义妮姬"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="{x:Type Button}">
            <Border x:Name="DeleteButtonBorder" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="1" CornerRadius="9">
              <Path Width="7.5" Height="7.5" HorizontalAlignment="Center" VerticalAlignment="Center"
                    Stroke="{TemplateBinding Foreground}" StrokeThickness="1.8" StrokeStartLineCap="Round" StrokeEndLineCap="Round"
                    Stretch="Fill" Data="M0,0 L8,8 M8,0 L0,8"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="DeleteButtonBorder" Property="Background" Value="#F0323A45"/>
              </Trigger>
              <Trigger Property="IsPressed" Value="True">
                <Setter TargetName="DeleteButtonBorder" Property="Background" Value="#FF0F151D"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
  </Window.Resources>
  <Border x:Name="RootBorder" CornerRadius="12" BorderThickness="1" Padding="22">
    <Grid>
      <Grid.RowDefinitions>
        <RowDefinition Height="Auto"/>
        <RowDefinition Height="Auto"/>
        <RowDefinition Height="*"/>
        <RowDefinition Height="Auto"/>
        <RowDefinition Height="Auto"/>
      </Grid.RowDefinitions>

      <StackPanel Grid.Row="0">
        <TextBlock x:Name="TitleText" Text="更新妮姬名单" FontSize="22" FontWeight="Bold"/>
        <TextBlock x:Name="HelpText" Text="该名单用于 OCR 角色名校准；珍藏品勾选会辅助过滤不可能出现的收藏图标误判。" FontSize="12" Margin="0,8,0,0" TextWrapping="Wrap"/>
        <TextBlock x:Name="UpdateTimeText" FontSize="12" Margin="0,8,0,0"/>
      </StackPanel>

      <StackPanel Grid.Row="1" Margin="0,18,0,8">
        <DockPanel>
          <TextBlock x:Name="ListTitleText" Text="已收录名单" FontSize="13" FontWeight="Bold" DockPanel.Dock="Left"/>
          <TextBlock x:Name="NameCountText" FontSize="12" HorizontalAlignment="Right" DockPanel.Dock="Right"/>
        </DockPanel>
        <TextBox x:Name="SearchNameBox" Height="32" Margin="0,10,0,0" FontSize="13" Padding="8,4"/>
      </StackPanel>

      <DataGrid x:Name="NameGrid"
                Grid.Row="2"
                AutoGenerateColumns="False"
                CanUserAddRows="False"
                CanUserDeleteRows="False"
                IsReadOnly="False"
                HeadersVisibility="Column"
                SelectionMode="Single"
                CanUserSortColumns="True"
                VerticalScrollBarVisibility="Auto"
                HorizontalScrollBarVisibility="Disabled"
                GridLinesVisibility="Horizontal"
                BorderThickness="1"
                FontSize="13"
                ColumnHeaderStyle="{StaticResource NameGridHeaderStyle}"
                CellStyle="{StaticResource NameGridCellStyle}">
        <DataGrid.Columns>
          <DataGridTemplateColumn Header="妮姬名字" SortMemberPath="Name" IsReadOnly="True" Width="*">
            <DataGridTemplateColumn.CellTemplate>
              <DataTemplate>
                <StackPanel Orientation="Horizontal" Margin="2,0,2,0">
                  <TextBlock Text="{Binding Name}" VerticalAlignment="Center" TextTrimming="CharacterEllipsis" MaxWidth="380"/>
                  <Button Tag="{Binding}" Style="{StaticResource NameGridDeleteButtonStyle}" Visibility="{Binding CanDelete, Converter={StaticResource BoolToVisibilityConverter}}"/>
                </StackPanel>
              </DataTemplate>
            </DataGridTemplateColumn.CellTemplate>
          </DataGridTemplateColumn>
          <DataGridCheckBoxColumn Header="珍藏品" Binding="{Binding HasCollection, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}" SortMemberPath="HasCollection" Width="92" ElementStyle="{StaticResource NameGridCollectionCheckBoxStyle}" EditingElementStyle="{StaticResource NameGridCollectionCheckBoxStyle}"/>
        </DataGrid.Columns>
      </DataGrid>

      <StackPanel Grid.Row="3" Margin="0,18,0,0">
        <TextBlock x:Name="InputLabelText" Text="输入新加入游戏的妮姬名字（一次只能输入一位）" FontSize="12" FontWeight="SemiBold"/>
        <StackPanel Orientation="Horizontal" Margin="0,8,0,0">
          <TextBox x:Name="NewNameBox" Width="300" Height="34" FontSize="14" Padding="8,5"/>
          <Button x:Name="RegisterNameButton" Width="82" Height="34" Content="登记" Margin="10,0,0,0"/>
        </StackPanel>
      </StackPanel>

      <StackPanel Grid.Row="4" Orientation="Horizontal" HorizontalAlignment="Right" Margin="0,20,0,0">
        <Button x:Name="CloseNameButton" Width="96" Height="34" Content="关闭" Margin="0,0,10,0"/>
        <Button x:Name="SaveNameButton" Width="132" Height="34" Content="保存并更新"/>
      </StackPanel>
    </Grid>
  </Border>
</Window>
"@

    $reader = New-Object System.Xml.XmlNodeReader ([xml]$managerXaml)
    $dialog = [Windows.Markup.XamlReader]::Load($reader)
    $dialog.Owner = $Window
    $dialog.ShowInTaskbar = $false

    $root = $dialog.FindName("RootBorder")
    $title = $dialog.FindName("TitleText")
    $help = $dialog.FindName("HelpText")
    $updateTime = $dialog.FindName("UpdateTimeText")
    $listTitle = $dialog.FindName("ListTitleText")
    $nameCount = $dialog.FindName("NameCountText")
    $searchBox = $dialog.FindName("SearchNameBox")
    $nameGrid = $dialog.FindName("NameGrid")
    $inputLabel = $dialog.FindName("InputLabelText")
    $newName = $dialog.FindName("NewNameBox")
    $registerButton = $dialog.FindName("RegisterNameButton")
    $closeButton = $dialog.FindName("CloseNameButton")
    $saveButton = $dialog.FindName("SaveNameButton")

    $converter = [Windows.Media.BrushConverter]::new()
    $colorConverter = [Windows.Media.ColorConverter]
    if ($CurrentTheme -eq "pink") {
        $dialog.Resources["NameGridHeaderBrush"].Color = $colorConverter::ConvertFromString("#FFFFDFEC")
        $dialog.Resources["NameGridHeaderTextBrush"].Color = $colorConverter::ConvertFromString("#6D344B")
        $dialog.Resources["NameGridBorderBrush"].Color = $colorConverter::ConvertFromString("#FFFFBCD5")
        $dialog.Resources["NameGridSelectionBrush"].Color = $colorConverter::ConvertFromString("#FFFFE8F2")
        $dialog.Resources["NameGridSelectionTextBrush"].Color = $colorConverter::ConvertFromString("#5B263C")
        $dialog.Resources["NameGridScrollThumbBrush"].Color = $colorConverter::ConvertFromString("#FFFF9FC5")
        $dialog.Resources["NameGridScrollTrackBrush"].Color = $colorConverter::ConvertFromString("#66FFF8FC")
        $root.Background = $converter.ConvertFromString("#F8FFF8FC")
        $root.BorderBrush = $converter.ConvertFromString("#FFFFBCD5")
        foreach ($text in @($title, $help, $updateTime, $listTitle, $nameCount, $inputLabel)) {
            $text.Foreground = $converter.ConvertFromString("#6D344B")
        }
        $searchBox.Background = $converter.ConvertFromString("#FFFFFFFF")
        $searchBox.Foreground = $converter.ConvertFromString("#6D344B")
        $searchBox.BorderBrush = $converter.ConvertFromString("#FFFFBCD5")
        $nameGrid.Background = $converter.ConvertFromString("#B8FFF8FC")
        $nameGrid.Foreground = $converter.ConvertFromString("#6D344B")
        $nameGrid.BorderBrush = $converter.ConvertFromString("#FFFFBCD5")
        $nameGrid.RowBackground = $converter.ConvertFromString("#66FFF8FC")
        $nameGrid.AlternatingRowBackground = $converter.ConvertFromString("#33FFDFEC")
        $nameGrid.HorizontalGridLinesBrush = $converter.ConvertFromString("#66FFBCD5")
        $newName.Background = $converter.ConvertFromString("#FFFFFFFF")
        $newName.Foreground = $converter.ConvertFromString("#6D344B")
        $newName.BorderBrush = $converter.ConvertFromString("#FFFFBCD5")
        $registerButton.Background = $converter.ConvertFromString("#EFFFF8FC")
        $registerButton.Foreground = $converter.ConvertFromString("#6D344B")
        $saveButton.Background = $converter.ConvertFromString("#FFFF9FC5")
        $saveButton.Foreground = $converter.ConvertFromString("#5B263C")
        $closeButton.Background = $converter.ConvertFromString("#EFFFF8FC")
        $closeButton.Foreground = $converter.ConvertFromString("#6D344B")
    } else {
        $dialog.Resources["NameGridHeaderBrush"].Color = $colorConverter::ConvertFromString("#122338")
        $dialog.Resources["NameGridHeaderTextBrush"].Color = $colorConverter::ConvertFromString("#F7FBFF")
        $dialog.Resources["NameGridBorderBrush"].Color = $colorConverter::ConvertFromString("#5EDCFF")
        $dialog.Resources["NameGridSelectionBrush"].Color = $colorConverter::ConvertFromString("#263F5F")
        $dialog.Resources["NameGridSelectionTextBrush"].Color = $colorConverter::ConvertFromString("#F7FBFF")
        $dialog.Resources["NameGridScrollThumbBrush"].Color = $colorConverter::ConvertFromString("#6BDFFF")
        $dialog.Resources["NameGridScrollTrackBrush"].Color = $colorConverter::ConvertFromString("#22324A")
        $root.Background = $converter.ConvertFromString("#F20B1424")
        $root.BorderBrush = $converter.ConvertFromString("#5EDCFF")
        foreach ($text in @($title, $help, $updateTime, $listTitle, $nameCount, $inputLabel)) {
            $text.Foreground = $converter.ConvertFromString("#F7FBFF")
        }
        $searchBox.Background = $converter.ConvertFromString("#44101A2A")
        $searchBox.Foreground = $converter.ConvertFromString("#F7FBFF")
        $searchBox.BorderBrush = $converter.ConvertFromString("#5EDCFF")
        $nameGrid.Background = $converter.ConvertFromString("#33101A2A")
        $nameGrid.Foreground = $converter.ConvertFromString("#F7FBFF")
        $nameGrid.BorderBrush = $converter.ConvertFromString("#5EDCFF")
        $nameGrid.RowBackground = $converter.ConvertFromString("#22101A2A")
        $nameGrid.AlternatingRowBackground = $converter.ConvertFromString("#3317253A")
        $nameGrid.HorizontalGridLinesBrush = $converter.ConvertFromString("#445EDCFF")
        $newName.Background = $converter.ConvertFromString("#44101A2A")
        $newName.Foreground = $converter.ConvertFromString("#F7FBFF")
        $newName.BorderBrush = $converter.ConvertFromString("#5EDCFF")
        $registerButton.Background = $converter.ConvertFromString("#22324A")
        $registerButton.Foreground = $converter.ConvertFromString("#F7FBFF")
        $saveButton.Background = $converter.ConvertFromString("#2EDCFF")
        $saveButton.Foreground = $converter.ConvertFromString("#03101D")
        $closeButton.Background = $converter.ConvertFromString("#22324A")
        $closeButton.Foreground = $converter.ConvertFromString("#F7FBFF")
    }

    $buildVisibleRows = {
        $filter = ([string]$searchBox.Text).Trim()
        $visibleRows = New-Object "System.Collections.ObjectModel.ObservableCollection[object]"
        foreach ($row in $allRows) {
            $rowName = [string]$row.Name
            if ([string]::IsNullOrWhiteSpace($filter) -or $rowName.IndexOf($filter, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
                [void]$visibleRows.Add($row)
            }
        }
        return ,$visibleRows
    }

    $countCollectionRows = {
        $count = 0
        foreach ($row in $allRows) {
            if ([bool]$row.HasCollection) { $count++ }
        }
        return $count
    }

    $refreshList = {
        try {
            $visibleRows = & $buildVisibleRows
            $nameGrid.ItemsSource = $visibleRows
            $collectionCount = & $countCollectionRows
            $nameCount.Text = ("当前显示 {0} / 共 {1} 位妮姬，珍藏品 {2} 位" -f $visibleRows.Count, $allRows.Count, $collectionCount)
            if (Test-Path $NikkeNameListPath) {
                $updateTime.Text = ("当前名单更新时间：{0}" -f (Get-Item -LiteralPath $NikkeNameListPath).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"))
            } else {
                $updateTime.Text = "当前名单更新时间：尚未创建"
            }
        } catch {
            $nameCount.Text = ("检索失败：{0}" -f $_.Exception.Message)
        }
    }
    & $refreshList

    $searchBox.Add_TextChanged({ & $refreshList })
    $searchBox.Add_PreviewKeyDown({
        param($sender, $eventArgs)
        if ($eventArgs.Key -eq [Windows.Input.Key]::Enter -or $eventArgs.Key -eq [Windows.Input.Key]::Return) {
            $eventArgs.Handled = $true
            & $refreshList
        }
    })
    $nameGrid.AddHandler(
        [System.Windows.Controls.Primitives.ButtonBase]::ClickEvent,
        [System.Windows.RoutedEventHandler]{
            param($sender, $eventArgs)
            $button = $eventArgs.OriginalSource
            if (-not ($button -is [System.Windows.Controls.Button])) { return }
            $targetRow = $button.Tag
            if (-not $targetRow -or -not [bool]$targetRow.CanDelete) { return }
            $eventArgs.Handled = $true
            $confirm = [System.Windows.MessageBox]::Show(
                $dialog,
                ("确认删除 [{0}] 吗？" -f $targetRow.Name),
                "确认删除",
                [System.Windows.MessageBoxButton]::YesNo,
                [System.Windows.MessageBoxImage]::Question
            )
            if ($confirm -ne [System.Windows.MessageBoxResult]::Yes) { return }
            [void]$allRows.Remove($targetRow)
            & $refreshList
        }
    )
    $closeButton.Add_Click({ $dialog.Close() })
    $registerName = {
        $rawValue = $newName.Text.Trim()
        if ($rawValue -match "[`r`n]") {
            [System.Windows.MessageBox]::Show($dialog, "一次只能输入一位妮姬名字。", "提示", [System.Windows.MessageBoxButton]::OK, [System.Windows.MessageBoxImage]::Information) | Out-Null
            return
        }
        $value = Normalize-NikkeNameForStorage $rawValue
        if (-not $value) {
            [System.Windows.MessageBox]::Show($dialog, "请输入需要登记的妮姬名字。", "提示", [System.Windows.MessageBoxButton]::OK, [System.Windows.MessageBoxImage]::Information) | Out-Null
            return
        }
        $exists = $false
        foreach ($row in $allRows) {
            if ((Normalize-NikkeNameForStorage $row.Name) -eq $value) {
                $exists = $true
                break
            }
        }
        if ($exists) {
            [System.Windows.MessageBox]::Show($dialog, "名单中已存在该妮姬名字。", "提示", [System.Windows.MessageBoxButton]::OK, [System.Windows.MessageBoxImage]::Information) | Out-Null
            return
        }
        [void]$allRows.Add([pscustomobject]@{
            Name = $value
            HasCollection = $false
            IsProtected = $false
            IsCollectionProtected = $false
            CanToggleCollection = $true
            CanDelete = $true
        })
        $newName.Text = ""
        $searchBox.Text = ""
        & $refreshList
        $nameGrid.ScrollIntoView($allRows[$allRows.Count - 1])
    }
    $registerButton.Add_Click({ & $registerName })
    $newName.Add_KeyDown({
        param($sender, $eventArgs)
        if ($eventArgs.Key -eq [Windows.Input.Key]::Enter -or $eventArgs.Key -eq [Windows.Input.Key]::Return) {
            $eventArgs.Handled = $true
            & $registerName
        }
    })

    $saveButton.Add_Click({
        $nameGrid.CommitEdit() | Out-Null
        $namesForSave = @($allRows | ForEach-Object { $_.Name })
        $collectionNamesForSave = @($allRows | Where-Object { [bool]$_.HasCollection } | ForEach-Object { $_.Name })
        $protectedNamesForSave = @($allRows | Where-Object { [bool]$_.IsProtected } | ForEach-Object { $_.Name })
        $protectedCollectionNamesForSave = @($allRows | Where-Object { [bool]$_.IsCollectionProtected } | ForEach-Object { $_.Name })
        Save-NikkeNameData $namesForSave $data.Source $collectionNamesForSave $protectedNamesForSave $protectedCollectionNamesForSave
        & $refreshList
        [System.Windows.MessageBox]::Show($dialog, "妮姬名单已更新。", "完成", [System.Windows.MessageBoxButton]::OK, [System.Windows.MessageBoxImage]::Information) | Out-Null
    })

    [void]$dialog.ShowDialog()
}

function Update-ModeButtonStyles {
    $primaryStyle = if ($CurrentTheme -eq "pink") { "PinkPrimaryButton" } else { "PrimaryButton" }
    $darkStyle = if ($CurrentTheme -eq "pink") { "PinkDarkButton" } else { "DarkButton" }
    Set-Style $ArenaButton $darkStyle
    Set-Style $SupportButton $darkStyle
    Set-Style $GroupButton $darkStyle
    Set-Style $Top8Button $darkStyle
    Set-Style $SeasonCaptureButton $darkStyle
    Set-Style $NikkeNameListButton $darkStyle
    Set-Style $PostDataOcrButton $darkStyle

    if ($CurrentTheme -eq "pink") {
        if ($CurrentCaptureMode -eq "support") { Set-Style $SupportButton $primaryStyle }
        elseif ($CurrentCaptureMode -eq "group") { Set-Style $GroupButton $primaryStyle }
        elseif ($CurrentCaptureMode -eq "top8") { Set-Style $Top8Button $primaryStyle }
        elseif ($CurrentCaptureMode -eq "season") { Set-Style $SeasonCaptureButton $primaryStyle }
        elseif ($CurrentCaptureMode -eq "ocr") { Set-Style $PostDataOcrButton $primaryStyle }
        elseif ($CurrentCaptureMode -eq "single") { Set-Style $ArenaButton $primaryStyle }
    } else {
        if ($CurrentCaptureMode -eq "support") { Set-Style $SupportButton $primaryStyle }
        elseif ($CurrentCaptureMode -eq "group") { Set-Style $GroupButton $primaryStyle }
        elseif ($CurrentCaptureMode -eq "top8") { Set-Style $Top8Button $primaryStyle }
        elseif ($CurrentCaptureMode -eq "season") { Set-Style $SeasonCaptureButton $primaryStyle }
        elseif ($CurrentCaptureMode -eq "ocr") { Set-Style $PostDataOcrButton $primaryStyle }
        elseif ($CurrentCaptureMode -eq "single") { Set-Style $ArenaButton $primaryStyle }
    }
}

function Set-TextTheme($Root, $Color) {
    if ($Root -is [Windows.Controls.TextBlock]) {
        $Root.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString($Color)
    }
    $count = [Windows.Media.VisualTreeHelper]::GetChildrenCount($Root)
    for ($i = 0; $i -lt $count; $i++) {
        Set-TextTheme ([Windows.Media.VisualTreeHelper]::GetChild($Root, $i)) $Color
    }
}

function New-GradientBrush($TopColor, $BottomColor) {
    $brush = New-Object Windows.Media.LinearGradientBrush
    $brush.StartPoint = [Windows.Point]::new(0, 0)
    $brush.EndPoint = [Windows.Point]::new(1, 1)
    $brush.GradientStops.Add([Windows.Media.GradientStop]::new(
        [Windows.Media.ColorConverter]::ConvertFromString($TopColor),
        0
    ))
    $brush.GradientStops.Add([Windows.Media.GradientStop]::new(
        [Windows.Media.ColorConverter]::ConvertFromString($BottomColor),
        1
    ))
    return $brush
}

function Apply-Theme($Theme) {
    $script:CurrentTheme = $Theme
    if ($Theme -eq "pink") {
        $BackgroundImage.Source = New-Bitmap $PinkBackgroundPath
        $BackgroundImage.RenderTransform = [Windows.Media.ScaleTransform]::new(1, 1)
        $OverlayA.Fill = [Windows.Media.BrushConverter]::new().ConvertFromString("#10FFF7FB")
        $OverlayB.Fill = [Windows.Media.BrushConverter]::new().ConvertFromString("#08FFFFFF")
        Set-Brush $MainPanel BorderBrush "#FFFFA9C8"
        Set-Brush $SubPagePanel BorderBrush "#FFFFA9C8"
        Set-Brush $ExampleBorder BorderBrush "#FFFFBCD5"
        Set-Brush $SettingsPanel BorderBrush "#FFFFBCD5"
        $MainPanel.Background = New-GradientBrush "#B8FFF8FC" "#AFFFF0F7"
        $SubPagePanel.Background = New-GradientBrush "#C2FFF8FC" "#B6FFF0F7"
        Set-Brush $ProcessCard BorderBrush "#FFFFC1D8"
        Set-Brush $ProcessCard Background "#AAFFFBFD"
        Set-Brush $LogCard BorderBrush "#FFFFC1D8"
        Set-Brush $LogCard Background "#A8FFF8FC"
        Set-TextTheme $Window "#6D344B"
        Set-Brush $LogText Foreground "#6D344B"
        Set-Style $ExecuteButton "PinkPrimaryButton"
        Set-Style $Group64Button "PinkDarkButton"
        Set-Style $Group32Button "PinkDarkButton"
        Set-Style $Group16Button "PinkDarkButton"
        Set-Style $Top8Button8 "PinkDarkButton"
        Set-Style $Top8Button4 "PinkDarkButton"
        Set-Style $Top8ButtonFinal "PinkDarkButton"
        Set-Style $Top8PyramidButton "PinkDarkButton"
        Set-Style $SeasonExecuteButton "PinkPrimaryButton"
        Set-Style $OcrRunButton "PinkPrimaryButton"
        Set-Style $OcrSelectFileButton "PinkDarkButton"
        Set-Style $OcrExampleButton "PinkDarkButton"
        Set-Style $OcrOpenFolderButton "PinkDarkButton"
        foreach ($slotButton in @($OcrSlotTop8Button, $OcrSlotGroup16Button, $OcrSlotGroup32Button, $OcrSlotGroup64Button)) {
            Set-Style $slotButton "OcrSlotButton"
        }
        Set-Brush $OcrUploadPanel BorderBrush "#FFFFBCD5"
        Set-Brush $OcrUploadPanel Background "#74FFF6FA"
        Set-Style $FolderButton "PinkDarkButton"
        Set-Style $SettingsButton "PinkDarkButton"
        Set-Style $BackButton "PinkDarkButton"
        Set-Style $ReservedButton1 "PinkMutedButton"
        Set-Style $ReservedButton2 "PinkMutedButton"
        foreach ($option in @($MarianFrameCheck, $DoroFrameCheck, $CinderellaFrameCheck, $CustomFrameCheck)) {
            Set-Style $option "PinkOptionCheck"
        }
        Set-Style $SupportStatusCheck "PinkOptionCheck"
        Set-Style $GroupSimpleDataCheck "PinkOptionCheck"
        Set-Style $GroupDetailedDataCheck "PinkOptionCheck"
        Set-Style $GroupAllDataCheck "PinkOptionCheck"
        Set-Style $ExportOcrDataCheck "PinkOptionCheck"
        Set-Style $OcrDebugCheck "PinkOptionCheck"
        Set-Style $LowMemoryCheck "PinkOptionCheck"
        Set-Style $OcrMediumMemoryCheck "PinkOptionCheck"
        foreach ($option in @($OcrEcoCheck, $OcrBalancedCheck, $OcrFullCheck, $OcrExtremeCheck, $OcrGpuCheck, $OcrThermalSafeCheck, $OcrThermalPerformanceCheck)) {
            Set-Style $option "PinkOptionCheck"
        }
        Set-Brush $ExportOcrTooltip Background "#F4FFF8FC"
        Set-Brush $ExportOcrTooltip BorderBrush "#FFFFBCD5"
        Set-Brush $ExportOcrTooltipText Foreground "#6D344B"
        Set-Brush $ExportOcrTooltipHintText Foreground "#6D344B"
        Set-Brush $LowMemoryTooltip Background "#F4FFF8FC"
        Set-Brush $LowMemoryTooltip BorderBrush "#FFFFBCD5"
        Set-Brush $LowMemoryTooltipText Foreground "#6D344B"
        Set-Brush $OcrMediumMemoryTooltip Background "#F4FFF8FC"
        Set-Brush $OcrMediumMemoryTooltip BorderBrush "#FFFFBCD5"
        Set-Brush $OcrMediumMemoryTooltipText Foreground "#6D344B"
        Set-Brush $OcrMediumMemoryDisabledText Foreground "#8A5B6E"
        Set-Brush $OcrThermalHintText Foreground "#8A5B6E"
        $MoonThemeButton.Background = [Windows.Media.BrushConverter]::new().ConvertFromString("#FFFFF8FC")
        $MoonThemeButton.BorderBrush = [Windows.Media.BrushConverter]::new().ConvertFromString("#FFFFA9C8")
        $MoonThemeButton.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString("#9B5572")
        foreach ($siteButton in @($SiteSkyxmoonButton, $SiteNikkeTopButton, $SiteMerlotJjcButton, $SiteGamekeeNikkeButton, $SiteBilibiliGuseButton, $SiteBilibiliDeen33Button)) {
            $siteButton.Background = [Windows.Media.BrushConverter]::new().ConvertFromString("#CCFFF8FC")
            $siteButton.BorderBrush = [Windows.Media.BrushConverter]::new().ConvertFromString("#FFFFBCD5")
        }
        $CaptureDelayBox.Background = [Windows.Media.BrushConverter]::new().ConvertFromString("#AAFFF8FC")
        $CaptureDelayBox.BorderBrush = [Windows.Media.BrushConverter]::new().ConvertFromString("#FFFFBCD5")
        $CaptureDelayBox.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString("#6D344B")
        $DetailDelayBox.Background = [Windows.Media.BrushConverter]::new().ConvertFromString("#AAFFF8FC")
        $DetailDelayBox.BorderBrush = [Windows.Media.BrushConverter]::new().ConvertFromString("#FFFFBCD5")
        $DetailDelayBox.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString("#6D344B")
        Set-Brush $OcrPerformanceWarningText Foreground "#B83D6A"
        Set-Brush $OcrGpuRecommendationText Foreground "#D4144C"
        Set-Brush $OcrGpuGuideLink Foreground "#B83D6A"
        Set-Brush $OcrParameterWarningText Foreground "#D4144C"
        Set-Brush $MainFullscreenHintText Foreground "#D4144C"
        Set-Brush $SeasonButtonHintText Foreground "#B83D6A"
        Set-Brush $HotkeyHintText Foreground "#B83D6A"
        $Window.Resources["ScrollThumbBrush"].Color = [Windows.Media.ColorConverter]::ConvertFromString("#FFFF9FC5")
        $Window.Resources["ScrollTrackBrush"].Color = [Windows.Media.ColorConverter]::ConvertFromString("#66FFF8FC")
        $SourceLink.NavigateUri = [Uri]::new($PinkSourceUrl)
        $SourceLink.Inlines.Clear()
        $SourceLink.Inlines.Add("Image source: Pixiewall Alice / Doro 5K")
        Update-ModeButtonStyles
    } else {
        $BackgroundImage.Source = New-Bitmap $DarkBackgroundPath
        $BackgroundImage.RenderTransform = [Windows.Media.ScaleTransform]::new(1, 1)
        $OverlayA.Fill = [Windows.Media.BrushConverter]::new().ConvertFromString("#44030712")
        $OverlayB.Fill = [Windows.Media.BrushConverter]::new().ConvertFromString("#18091423")
        Set-Brush $MainPanel BorderBrush "#766BDFFF"
        Set-Brush $SubPagePanel BorderBrush "#766BDFFF"
        Set-Brush $ExampleBorder BorderBrush "#5EDCFF"
        Set-Brush $SettingsPanel BorderBrush "#5EDCFF"
        $MainPanel.Background = New-GradientBrush "#CC111C2F" "#BA07101E"
        $SubPagePanel.Background = New-GradientBrush "#CC111C2F" "#BA07101E"
        Set-Brush $ProcessCard BorderBrush "#355875"
        Set-Brush $ProcessCard Background "#66101A2A"
        Set-Brush $LogCard BorderBrush "#365875"
        Set-Brush $LogCard Background "#8A06101E"
        Set-TextTheme $Window "#F7FBFF"
        Set-Brush $LogText Foreground "#BBD0E1"
        Set-Style $ExecuteButton "PrimaryButton"
        Set-Style $Group64Button "DarkButton"
        Set-Style $Group32Button "DarkButton"
        Set-Style $Group16Button "DarkButton"
        Set-Style $Top8Button8 "DarkButton"
        Set-Style $Top8Button4 "DarkButton"
        Set-Style $Top8ButtonFinal "DarkButton"
        Set-Style $Top8PyramidButton "DarkButton"
        Set-Style $SeasonExecuteButton "PrimaryButton"
        Set-Style $OcrRunButton "PrimaryButton"
        Set-Style $OcrSelectFileButton "DarkButton"
        Set-Style $OcrExampleButton "DarkButton"
        Set-Style $OcrOpenFolderButton "DarkButton"
        foreach ($slotButton in @($OcrSlotTop8Button, $OcrSlotGroup16Button, $OcrSlotGroup32Button, $OcrSlotGroup64Button)) {
            Set-Style $slotButton "OcrSlotButton"
        }
        Set-Brush $OcrUploadPanel BorderBrush "#5EDCFF"
        Set-Brush $OcrUploadPanel Background "#44101A2A"
        Set-Style $FolderButton "DarkButton"
        Set-Style $SettingsButton "DarkButton"
        Set-Style $BackButton "DarkButton"
        Set-Style $ReservedButton1 "MutedButton"
        Set-Style $ReservedButton2 "MutedButton"
        foreach ($option in @($MarianFrameCheck, $DoroFrameCheck, $CinderellaFrameCheck, $CustomFrameCheck)) {
            Set-Style $option "DarkOptionCheck"
        }
        Set-Style $SupportStatusCheck "DarkOptionCheck"
        Set-Style $GroupSimpleDataCheck "DarkOptionCheck"
        Set-Style $GroupDetailedDataCheck "DarkOptionCheck"
        Set-Style $GroupAllDataCheck "DarkOptionCheck"
        Set-Style $ExportOcrDataCheck "DarkOptionCheck"
        Set-Style $OcrDebugCheck "DarkOptionCheck"
        Set-Style $LowMemoryCheck "DarkOptionCheck"
        Set-Style $OcrMediumMemoryCheck "DarkOptionCheck"
        foreach ($option in @($OcrEcoCheck, $OcrBalancedCheck, $OcrFullCheck, $OcrExtremeCheck, $OcrGpuCheck, $OcrThermalSafeCheck, $OcrThermalPerformanceCheck)) {
            Set-Style $option "DarkOptionCheck"
        }
        Set-Brush $ExportOcrTooltip Background "#F20B1424"
        Set-Brush $ExportOcrTooltip BorderBrush "#5EDCFF"
        Set-Brush $ExportOcrTooltipText Foreground "#F7FBFF"
        Set-Brush $ExportOcrTooltipHintText Foreground "#F7FBFF"
        Set-Brush $LowMemoryTooltip Background "#F20B1424"
        Set-Brush $LowMemoryTooltip BorderBrush "#5EDCFF"
        Set-Brush $LowMemoryTooltipText Foreground "#F7FBFF"
        Set-Brush $OcrMediumMemoryTooltip Background "#F20B1424"
        Set-Brush $OcrMediumMemoryTooltip BorderBrush "#5EDCFF"
        Set-Brush $OcrMediumMemoryTooltipText Foreground "#F7FBFF"
        Set-Brush $OcrMediumMemoryDisabledText Foreground "#A9C2D9"
        Set-Brush $OcrThermalHintText Foreground "#A9C2D9"
        $MoonThemeButton.Background = [Windows.Media.BrushConverter]::new().ConvertFromString("#243750")
        $MoonThemeButton.BorderBrush = [Windows.Media.BrushConverter]::new().ConvertFromString("#80E8FF")
        $MoonThemeButton.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString("#DDF7FF")
        foreach ($siteButton in @($SiteSkyxmoonButton, $SiteNikkeTopButton, $SiteMerlotJjcButton, $SiteGamekeeNikkeButton, $SiteBilibiliGuseButton, $SiteBilibiliDeen33Button)) {
            $siteButton.Background = [Windows.Media.BrushConverter]::new().ConvertFromString("#66101A2A")
            $siteButton.BorderBrush = [Windows.Media.BrushConverter]::new().ConvertFromString("#6BDFFF")
        }
        $CaptureDelayBox.Background = [Windows.Media.BrushConverter]::new().ConvertFromString("#44101A2A")
        $CaptureDelayBox.BorderBrush = [Windows.Media.BrushConverter]::new().ConvertFromString("#5EDCFF")
        $CaptureDelayBox.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString("#F7FBFF")
        $DetailDelayBox.Background = [Windows.Media.BrushConverter]::new().ConvertFromString("#44101A2A")
        $DetailDelayBox.BorderBrush = [Windows.Media.BrushConverter]::new().ConvertFromString("#5EDCFF")
        $DetailDelayBox.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString("#F7FBFF")
        Set-Brush $OcrPerformanceWarningText Foreground "#FFD58A"
        Set-Brush $OcrGpuRecommendationText Foreground "#FFE45C"
        Set-Brush $OcrGpuGuideLink Foreground "#64E7FF"
        Set-Brush $OcrParameterWarningText Foreground "#FFE45C"
        Set-Brush $MainFullscreenHintText Foreground "#FFE45C"
        Set-Brush $SeasonButtonHintText Foreground "#FFD58A"
        Set-Brush $HotkeyHintText Foreground "#FFD38A"
        $Window.Resources["ScrollThumbBrush"].Color = [Windows.Media.ColorConverter]::ConvertFromString("#6BDFFF")
        $Window.Resources["ScrollTrackBrush"].Color = [Windows.Media.ColorConverter]::ConvertFromString("#22324A")
        $SourceLink.NavigateUri = [Uri]::new($DarkSourceUrl)
        $SourceLink.Inlines.Clear()
        $SourceLink.Inlines.Add("Image source: Pixiewall Rapi / Drake / Laplace")
        Update-ModeButtonStyles
    }
}

function Set-Log($Text) {
    $LogText.Text = $Text
}

function Append-Log($Text) {
    $lines = @()
    if ($LogText.Text) { $lines += $LogText.Text -split "`r?`n" }
    $lines += $Text
    if ($lines.Count -gt 8) { $lines = $lines[($lines.Count - 8)..($lines.Count - 1)] }
    $LogText.Text = ($lines -join "`n")
}

function New-CaptureDiagnosticsLog([string]$Mode) {
    try {
        $logDirectory = Join-Path $OutputRoot "logs"
        New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
        $stamp = Get-Date -Format "yyyyMMdd_HHmmss_fff"
        $safeMode = if ($Mode) { $Mode -replace "[^A-Za-z0-9_-]", "_" } else { "capture" }
        $path = Join-Path $logDirectory ("capture_{0}_{1}.log" -f $stamp, $safeMode)
        [IO.File]::WriteAllText($path, ("[{0}] capture requested`r`n" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff")), [Text.UTF8Encoding]::new($false))
        return $path
    } catch {
        return $null
    }
}

function Add-CaptureDiagnosticsLog($Path, [string]$Text) {
    if (-not $Path) { return }
    try {
        $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss.fff"), $Text
        [IO.File]::AppendAllText($Path, ($line + [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
    } catch {}
}

function Set-Running($Running) {
    $ArenaButton.IsEnabled = -not $Running
    $SupportButton.IsEnabled = -not $Running
    $GroupButton.IsEnabled = -not $Running
    $Top8Button.IsEnabled = -not $Running
    $SeasonCaptureButton.IsEnabled = -not $Running
    $NikkeNameListButton.IsEnabled = -not $Running
    $PostDataOcrButton.IsEnabled = -not $Running
    $ExecuteButton.IsEnabled = -not $Running
    $Group64Button.IsEnabled = -not $Running
    $Group32Button.IsEnabled = -not $Running
    $Group16Button.IsEnabled = -not $Running
    $Top8Button8.IsEnabled = -not $Running
    $Top8Button4.IsEnabled = -not $Running
    $Top8ButtonFinal.IsEnabled = -not $Running
    $Top8PyramidButton.IsEnabled = -not $Running
    $SeasonExecuteButton.IsEnabled = -not $Running
    foreach ($control in @(
        $OcrRunButton,
        $OcrSelectFileButton,
        $OcrExampleButton,
        $OcrSlotTop8Button,
        $OcrSlotGroup16Button,
        $OcrSlotGroup32Button,
        $OcrSlotGroup64Button,
        $OcrSlotTop8ClearButton,
        $OcrSlotGroup16ClearButton,
        $OcrSlotGroup32ClearButton,
        $OcrSlotGroup64ClearButton
    )) {
        if ($control) { $control.IsEnabled = -not $Running }
    }
    # NIKKE_DISABLED_LOW_MEMORY_20260630: Low-memory mode is retained in code but hidden until it is worth restoring.
    $LowMemoryCheck.IsEnabled = $false
    $LowMemoryCheck.IsChecked = $false
    $LowMemoryCheck.Visibility = "Collapsed"
    # NIKKE_DISABLED_MEDIUM_MEMORY_20260630: Manifest/mid-memory OCR mode is parked for now because it is too slow.
    $OcrMediumMemoryCheck.IsEnabled = $false
    $OcrMediumMemoryCheck.IsChecked = $false
    $OcrMediumMemoryCheck.Opacity = 0.45
    # NIKKE_DISABLED_AUTO_OCR_EXPORT_20260630: Capture-time JSON/Excel export is parked; manual upload OCR remains active.
    $ExportOcrDataCheck.IsEnabled = $false
    $ExportOcrDataCheck.IsChecked = $false
    $ExportOcrDataCheck.Opacity = 0.45
    if ($Running) {
        $StatusText.Text = $TextRunning
        $StatusText.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString("#FFD38A")
    } else {
        $StatusText.Text = $TextIdle
        $StatusText.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString("#68F2C2")
    }
}

function Update-Process-Status {
    if ([NativeWin]::IsNikkeRunning()) {
        $ProcessStatusText.Text = "Running"
        $ProcessStatusText.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString("#68F2C2")
    } else {
        $ProcessStatusText.Text = "Not detected"
        $ProcessStatusText.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString("#FFD38A")
    }
}

$ExampleImage.Source = New-Bitmap $ExamplePath
$DoroImage.Source = New-Bitmap $DoroPath
$CaptureDelaySlider.Minimum = $DelayMinSeconds
$CaptureDelaySlider.Maximum = 5
$CaptureDelaySlider.Value = $CaptureDelaySeconds
$CaptureDelayBox.Text = ("{0:0.00}" -f $CaptureDelaySeconds)
$DetailDelaySlider.Minimum = $DetailDelayMinSeconds
$DetailDelaySlider.Maximum = 5
$DetailDelaySlider.Value = $DetailCaptureDelaySeconds
$DetailDelayBox.Text = ("{0:0.00}" -f $DetailCaptureDelaySeconds)
New-Item -ItemType Directory -Force -Path $CustomFrameDir | Out-Null
New-Item -ItemType Directory -Force -Path $SupportCustomFrameDir | Out-Null
New-Item -ItemType Directory -Force -Path $GroupCustomFrameDir | Out-Null
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
Apply-Theme "dark"
Update-Process-Status

$timer = New-Object Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromSeconds(2)
$timer.Add_Tick({ Update-Process-Status })
$timer.Start()

$SourceLink.Add_RequestNavigate({
    Start-Process $SourceLink.NavigateUri.AbsoluteUri
})

function Open-SiteUrl([string]$Url) {
    if ($Url) {
        Start-Process $Url
    }
}

if ($OcrGpuGuideLink) {
    $OcrGpuGuideLink.Add_Click({
        $guidePath = Join-Path $ScriptDir "GPU_OCR_RUNTIME_SETUP_GUIDE.pdf"
        if (Test-Path $guidePath) {
            Start-Process -FilePath $guidePath
        } else {
            Append-Log "未找到 GPU 环境配置教程 PDF：$guidePath"
        }
    })
}

if ($SiteSkyxmoonButton) { $SiteSkyxmoonButton.Add_Click({ Open-SiteUrl $SiteSkyxmoonUrl }) }
if ($SiteNikkeTopButton) { $SiteNikkeTopButton.Add_Click({ Open-SiteUrl $SiteNikkeTopUrl }) }
if ($SiteMerlotJjcButton) { $SiteMerlotJjcButton.Add_Click({ Open-SiteUrl $SiteMerlotJjcUrl }) }
if ($SiteGamekeeNikkeButton) { $SiteGamekeeNikkeButton.Add_Click({ Open-SiteUrl $SiteGamekeeNikkeUrl }) }
if ($SiteBilibiliGuseButton) { $SiteBilibiliGuseButton.Add_Click({ Open-SiteUrl $SiteBilibiliGuseUrl }) }
if ($SiteBilibiliDeen33Button) { $SiteBilibiliDeen33Button.Add_Click({ Open-SiteUrl $SiteBilibiliDeen33Url }) }

$MoonThemeButton.Add_Click({ Apply-Theme "dark" })
$DoroThemeButton.Add_Click({ Apply-Theme "pink" })

function Set-JsonProperty($Object, [string]$Name, $Value) {
    if ($null -eq $Object) { return }
    if ($Object.PSObject.Properties[$Name]) {
        $Object.$Name = $Value
    } else {
        Add-Member -InputObject $Object -MemberType NoteProperty -Name $Name -Value $Value
    }
}

function Save-CaptureTimingSettings {
    if (-not $script:SettingsInitialized) { return }
    try {
        if (Test-Path $RoundConfigPath) {
            $configJson = Get-Content -LiteralPath $RoundConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
        } else {
            $configJson = [pscustomobject]@{}
        }
        if (-not $configJson.PSObject.Properties["timing"] -or $null -eq $configJson.timing) {
            Add-Member -InputObject $configJson -MemberType NoteProperty -Name "timing" -Value ([pscustomobject]@{}) -Force
        }
        if (-not $configJson.PSObject.Properties["launcher_settings"] -or $null -eq $configJson.launcher_settings) {
            Add-Member -InputObject $configJson -MemberType NoteProperty -Name "launcher_settings" -Value ([pscustomobject]@{}) -Force
        }

        $clickDelay = [Math]::Round([double]$script:CaptureDelaySeconds, 2)
        foreach ($key in @(
            "after_round_click_seconds",
            "after_avatar_click_seconds",
            "after_support_avatar_click_seconds",
            "after_group_avatar_click_seconds",
            "after_group_tab_click_seconds",
            "after_group_result_click_seconds",
            "after_outpost_click_seconds"
        )) {
            Set-JsonProperty $configJson.timing $key $clickDelay
        }
        Set-JsonProperty $configJson.timing "after_group_detail_click_seconds" ([Math]::Round([double]$script:DetailCaptureDelaySeconds, 2))
        Set-JsonProperty $configJson.launcher_settings "ocr_performance_mode" ([string]$script:OcrPerformanceMode)
        Set-JsonProperty $configJson.launcher_settings "ocr_thermal_mode" ([string]$script:OcrThermalMode)

        $json = $configJson | ConvertTo-Json -Depth 20
        $encoding = [Text.UTF8Encoding]::new($false)
        [IO.File]::WriteAllText($RoundConfigPath, $json + [Environment]::NewLine, $encoding)
    } catch {
        Append-Log ("Failed to save capture settings: " + $_.Exception.Message)
    }
}

function Set-CaptureDelay($Value) {
    $valueNumber = [double]$Value
    $valueNumber = [Math]::Max($DelayMinSeconds, [Math]::Min(5.0, $valueNumber))
    $valueNumber = [Math]::Round($valueNumber, 2)
    $script:CaptureDelaySeconds = $valueNumber
    if ([Math]::Abs($CaptureDelaySlider.Value - $valueNumber) -gt 0.001) {
        $CaptureDelaySlider.Value = $valueNumber
    }
    $CaptureDelayBox.Text = ("{0:0.00}" -f $valueNumber)
    Save-CaptureTimingSettings
}

$CaptureDelaySlider.Add_ValueChanged({
    Set-CaptureDelay $CaptureDelaySlider.Value
})

function Commit-CaptureDelayBox {
    $parsed = 0.0
    if ([double]::TryParse($CaptureDelayBox.Text, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)) {
        Set-CaptureDelay $parsed
    } else {
        $CaptureDelayBox.Text = ("{0:0.00}" -f $CaptureDelaySeconds)
    }
}

$CaptureDelayBox.Add_LostFocus({ Commit-CaptureDelayBox })
$CaptureDelayBox.Add_KeyDown({
    param($sender, $eventArgs)
    if ($eventArgs.Key -eq [Windows.Input.Key]::Enter) {
        Commit-CaptureDelayBox
        $eventArgs.Handled = $true
    }
})

function Set-DetailCaptureDelay($Value) {
    $valueNumber = [double]$Value
    $valueNumber = [Math]::Max($DetailDelayMinSeconds, [Math]::Min(5.0, $valueNumber))
    $valueNumber = [Math]::Round($valueNumber, 2)
    $script:DetailCaptureDelaySeconds = $valueNumber
    if ([Math]::Abs($DetailDelaySlider.Value - $valueNumber) -gt 0.001) {
        $DetailDelaySlider.Value = $valueNumber
    }
    $DetailDelayBox.Text = ("{0:0.00}" -f $valueNumber)
    Save-CaptureTimingSettings
}

$DetailDelaySlider.Add_ValueChanged({
    Set-DetailCaptureDelay $DetailDelaySlider.Value
})

function Commit-DetailDelayBox {
    $parsed = 0.0
    if ([double]::TryParse($DetailDelayBox.Text, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)) {
        Set-DetailCaptureDelay $parsed
    } else {
        $DetailDelayBox.Text = ("{0:0.00}" -f $DetailCaptureDelaySeconds)
    }
}

$DetailDelayBox.Add_LostFocus({ Commit-DetailDelayBox })
$DetailDelayBox.Add_KeyDown({
    param($sender, $eventArgs)
    if ($eventArgs.Key -eq [Windows.Input.Key]::Enter) {
        Commit-DetailDelayBox
        $eventArgs.Handled = $true
    }
})

function Set-OcrPerformanceMode($Mode) {
    if ($Mode -eq "gpu" -and -not $OcrGpuAvailable) { $Mode = "cpu" }
    if ($Mode -notin @("cpu", "gpu")) { $Mode = "cpu" }
    $script:OcrPerformanceMode = $Mode
    if ($OcrEcoCheck) { $OcrEcoCheck.IsChecked = $false }
    if ($OcrBalancedCheck) { $OcrBalancedCheck.IsChecked = $false }
    if ($OcrFullCheck) { $OcrFullCheck.IsChecked = ($Mode -eq "cpu") }
    if ($OcrExtremeCheck) { $OcrExtremeCheck.IsChecked = $false }
    if ($OcrGpuCheck) { $OcrGpuCheck.IsChecked = ($Mode -eq "gpu") }
    Save-CaptureTimingSettings
}

function Get-OcrPerformanceConfig {
    return @{ UseGpu = ($OcrPerformanceMode -eq "gpu" -and $OcrGpuAvailable) }
}

function Get-ActiveOcrPythonExe($Config) {
    if ($Config -and $Config.UseGpu -and $OcrGpuPythonExe) {
        return $OcrGpuPythonExe
    }
    return $OcrPythonExe
}

function Apply-OcrProcessEnvironment($ProcessStartInfo, $Config) {
    return
}

function Show-OcrPerformancePriorityWarning {
    $message = @"
指挥官，您正在切换至“性能优先模式”。

该模式将优先保证识别速度，程序不会在中高温阶段主动降速，因此 CPU 或 GPU 可能持续处于高负载状态。长时间运行可能导致设备温度升高、风扇高速运转、性能降频，极端情况下可能触发系统硬件保护并导致自动关机。

切换到性能优先模式后，程序不会主动在 block 之间等待，也不会在 80°C、86°C 阶段主动降速或暂停。为保护设备，程序仍会保留可读取温度下的 92°C 紧急暂停；如果温度传感器无法读取，程序无法保证硬性温度暂停生效。

如果您不确定当前散热状态，建议继续使用默认的“过热保护模式”。

是否仍要启用“性能优先模式”？

选择“是”继续启用性能优先模式；选择“否”返回过热保护模式。
"@
    try {
        $result = [System.Windows.MessageBox]::Show(
            $Window,
            $message,
            "性能优先模式确认",
            [System.Windows.MessageBoxButton]::YesNo,
            [System.Windows.MessageBoxImage]::Warning
        )
        return ($result -eq [System.Windows.MessageBoxResult]::Yes)
    } catch {
        return $false
    }
}

function Set-OcrThermalMode($Mode, [bool]$SkipConfirm = $false) {
    if ($Mode -notin @("safe", "performance")) { $Mode = "safe" }
    if ($Mode -eq "performance" -and -not $SkipConfirm) {
        if (-not (Show-OcrPerformancePriorityWarning)) {
            $Mode = "safe"
        }
    }
    $script:OcrThermalMode = $Mode
    if ($OcrThermalSafeCheck) { $OcrThermalSafeCheck.IsChecked = ($Mode -eq "safe") }
    if ($OcrThermalPerformanceCheck) { $OcrThermalPerformanceCheck.IsChecked = ($Mode -eq "performance") }
    if ($OcrThermalHintText) {
        if ($Mode -eq "performance") {
            $OcrThermalHintText.Text = "性能优先模式不会在 block 之间主动等待；仅保留可读取温度下的 92°C 紧急暂停与用户终止任务能力。"
        } else {
            $OcrThermalHintText.Text = "过热保护模式不限制线程，仅在每个对局 block 结束后短暂间歇，降低长时间持续满载的概率。"
        }
    }
    Save-CaptureTimingSettings
}

function Get-OcrThermalConfig {
    $mode = if ($script:OcrThermalMode -eq "performance") { "performance" } else { "safe" }
    $sleep = if ($mode -eq "safe") { [double]$script:OcrSafeCooldownSeconds } else { 0.0 }
    return @{ Mode = $mode; CooldownSleep = $sleep }
}

$OcrEcoCheck.Add_Click({ Set-OcrPerformanceMode "cpu" })
$OcrBalancedCheck.Add_Click({ Set-OcrPerformanceMode "cpu" })
$OcrFullCheck.Add_Click({ Set-OcrPerformanceMode "cpu" })
$OcrExtremeCheck.Add_Click({ Set-OcrPerformanceMode "cpu" })
$OcrGpuCheck.Add_Click({ Set-OcrPerformanceMode "gpu" })
$OcrThermalSafeCheck.Add_Click({ Set-OcrThermalMode "safe" $true })
$OcrThermalPerformanceCheck.Add_Click({ Set-OcrThermalMode "performance" $false })
$OcrGpuCheck.IsEnabled = $OcrGpuAvailable
if ($OcrGpuAvailable) {
    $OcrGpuCheck.Opacity = 1.0
    $OcrGpuCheck.ToolTip = "GPU 模式可用；选择 GPU 后使用独立 GPU PaddleOCR 运行环境。"
    $OcrGpuStatusText.Text = "GPU 模式可用；选择 GPU 后使用独立 GPU PaddleOCR 运行环境。"
} else {
    $OcrGpuCheck.Opacity = 0.38
    $OcrGpuCheck.ToolTip = "GPU 不可用：未找到可用的独立 GPU PaddleOCR 运行环境。"
    $OcrGpuStatusText.Text = "GPU 不可用：未找到可用的独立 GPU PaddleOCR 运行环境。"
}
Set-OcrPerformanceMode $ConfiguredOcrPerformanceMode
Set-OcrThermalMode $ConfiguredOcrThermalMode $true
$script:SettingsInitialized = $true

# NIKKE_DISABLED_OCR_PERFORMANCE_LIMITS_20260701:
# The previous performance profiles are parked here. The launcher no longer
# passes --cpu-threads, sets process priority, or writes OMP/MKL thread env vars.
<#
function Set-OcrPerformanceMode($Mode) {
    if ($Mode -eq "gpu" -and -not $OcrGpuAvailable) {
        $Mode = "balanced"
    }
    $script:OcrPerformanceMode = $Mode
    $OcrEcoCheck.IsChecked = ($Mode -eq "eco")
    $OcrBalancedCheck.IsChecked = ($Mode -eq "balanced")
    $OcrFullCheck.IsChecked = ($Mode -eq "full")
    $OcrExtremeCheck.IsChecked = ($Mode -eq "extreme")
    $OcrGpuCheck.IsChecked = ($Mode -eq "gpu")
}

function Get-OcrPerformanceConfig {
    $processorCount = [Math]::Max(1, [Environment]::ProcessorCount)
    switch ($OcrPerformanceMode) {
        "eco" { return @{ Threads = [Math]::Min(2, $processorCount); UseGpu = $false; Priority = "BelowNormal"; Aggressive = $false } }
        "full" { return @{ Threads = $processorCount; UseGpu = $false; Priority = "Normal"; Aggressive = $false } }
        "extreme" { return @{ Threads = $processorCount; UseGpu = $false; Priority = "High"; Aggressive = $true } }
        "gpu" {
            if ($OcrGpuAvailable) {
                return @{ Threads = [Math]::Min(2, $processorCount); UseGpu = $true; Priority = "Normal"; Aggressive = $false }
            }
        }
    }
    return @{ Threads = [Math]::Min(4, $processorCount); UseGpu = $false; Priority = "BelowNormal"; Aggressive = $false }
}

function Apply-OcrProcessEnvironment($ProcessStartInfo, $Config) {
    $threadText = [string]$Config.Threads
    $ProcessStartInfo.EnvironmentVariables["OMP_NUM_THREADS"] = $threadText
    $ProcessStartInfo.EnvironmentVariables["MKL_NUM_THREADS"] = $threadText
    if ($Config.Aggressive) {
        $ProcessStartInfo.EnvironmentVariables["OMP_DYNAMIC"] = "FALSE"
        $ProcessStartInfo.EnvironmentVariables["MKL_DYNAMIC"] = "FALSE"
        $ProcessStartInfo.EnvironmentVariables["KMP_BLOCKTIME"] = "200"
    }
}
#>
# NIKKE_DISABLED_LOW_MEMORY_20260630: Low-memory mode is temporarily removed from the GUI.
$script:LowMemoryMode = $false
$LowMemoryCheck.IsChecked = $false
$LowMemoryCheck.IsEnabled = $false
$LowMemoryCheck.Visibility = "Collapsed"
<#
$LowMemoryCheck.IsChecked = $LowMemoryMode
$LowMemoryCheck.Add_Click({
    $script:LowMemoryMode = [bool]$LowMemoryCheck.IsChecked
})
#>

# NIKKE_DISABLED_MEDIUM_MEMORY_20260630: Manifest/mid-memory OCR mode is kept for later restoration but cannot be selected now.
$script:OcrMediumMemoryMode = $false
$OcrMediumMemoryCheck.IsChecked = $false
$OcrMediumMemoryCheck.IsEnabled = $false
$OcrMediumMemoryCheck.Opacity = 0.45
<#
$OcrMediumMemoryCheck.IsChecked = $OcrMediumMemoryMode
$OcrMediumMemoryCheck.Add_Click({
    $script:OcrMediumMemoryMode = [bool]$OcrMediumMemoryCheck.IsChecked
})
#>

function Test-OcrMediumMemoryMode {
    # NIKKE_DISABLED_MEDIUM_MEMORY_20260630: Force direct large-image OCR until this mode is deliberately restored.
    <#
    try {
        if ($OcrMediumMemoryCheck) {
            return [bool]$OcrMediumMemoryCheck.IsChecked
        }
    } catch {}
    return [bool]$script:OcrMediumMemoryMode
    #>
    return $false
}

function Test-AutoOcrExportRequested {
    # NIKKE_DISABLED_AUTO_OCR_EXPORT_20260630: Capture-time JSON/Excel export is parked; manual upload OCR remains active.
    <#
    try {
        if ($ExportOcrDataCheck) {
            return [bool]$ExportOcrDataCheck.IsChecked
        }
    } catch {}
    #>
    return $false
}

function Add-OcrRecognitionOptionArguments([string]$Arguments) {
    try {
        if ($OcrPowerCheck -and -not [bool]$OcrPowerCheck.IsChecked) {
            $Arguments += " --no-power"
        }
        if ($OcrCollectionCheck -and -not [bool]$OcrCollectionCheck.IsChecked) {
            $Arguments += " --no-collection"
        }
        if ($OcrStatLevelCheck -and -not [bool]$OcrStatLevelCheck.IsChecked) {
            $Arguments += " --no-stat-levels"
        }
    } catch {}
    return $Arguments
}

$ExportOcrDataCheck.IsChecked = $false
$ExportOcrDataCheck.IsEnabled = $false
$ExportOcrDataCheck.Opacity = 0.45

function Clear-OtherFrameChecks($Selected) {
    foreach ($option in @($MarianFrameCheck, $DoroFrameCheck, $CinderellaFrameCheck, $CustomFrameCheck)) {
        if ($option -ne $Selected) { $option.IsChecked = $false }
    }
}

foreach ($option in @($MarianFrameCheck, $DoroFrameCheck, $CinderellaFrameCheck, $CustomFrameCheck)) {
    $option.Add_Click({
        param($sender, $eventArgs)
        if ($sender.IsChecked) { Clear-OtherFrameChecks $sender }
    })
}

$GroupSimpleDataCheck.Add_Click({
    if ($CurrentCaptureMode -eq "season") {
        $GroupSimpleDataCheck.IsChecked = $false
        $GroupDetailedDataCheck.IsChecked = $true
        return
    }
    if ($GroupSimpleDataCheck.IsChecked) {
        $GroupDetailedDataCheck.IsChecked = $false
        $ExportOcrDataCheck.IsChecked = $false
    }
})

$GroupDetailedDataCheck.Add_Click({
    if ($CurrentCaptureMode -eq "season") {
        $GroupDetailedDataCheck.IsChecked = $true
        return
    }
    if ($GroupDetailedDataCheck.IsChecked) { $GroupSimpleDataCheck.IsChecked = $false }
})

function Get-CustomFramePath {
    if ($CurrentCaptureMode -eq "support") {
        $dir = $SupportCustomFrameDir
    } elseif ($CurrentCaptureMode -eq "group" -or $CurrentCaptureMode -eq "top8" -or $CurrentCaptureMode -eq "season") {
        $dir = $GroupCustomFrameDir
    } else {
        $dir = $CustomFrameDir
    }
    $file = Get-ChildItem -LiteralPath $dir -File |
        Where-Object { $_.Extension -match '^\.(jpg|jpeg|png)$' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($file) { return $file.FullName }
    if ($CurrentCaptureMode -eq "support") { return (Resolve-ImageVariant $SupportMarianFramePath) }
    if ($CurrentCaptureMode -eq "group" -or $CurrentCaptureMode -eq "top8" -or $CurrentCaptureMode -eq "season") { return (Resolve-ImageVariant $GroupMarianFramePath) }
    return (Resolve-ImageVariant $MarianFramePath)
}

function Get-SelectedFramePath {
    if ($CurrentCaptureMode -eq "support") {
        if ($MarianFrameCheck.IsChecked) { return (Resolve-ImageVariant $SupportMarianFramePath) }
        if ($DoroFrameCheck.IsChecked) { return (Resolve-ImageVariant $SupportDoroFramePath) }
        if ($CinderellaFrameCheck.IsChecked) { return (Resolve-ImageVariant $SupportCinderellaFramePath) }
    } elseif ($CurrentCaptureMode -eq "group" -or $CurrentCaptureMode -eq "top8" -or $CurrentCaptureMode -eq "season") {
        if ($MarianFrameCheck.IsChecked) { return (Resolve-ImageVariant $GroupMarianFramePath) }
        if ($DoroFrameCheck.IsChecked) { return (Resolve-ImageVariant $GroupDoroFramePath) }
        if ($CinderellaFrameCheck.IsChecked) { return (Resolve-ImageVariant $GroupCinderellaFramePath) }
    } else {
        if ($MarianFrameCheck.IsChecked) { return (Resolve-ImageVariant $MarianFramePath) }
        if ($DoroFrameCheck.IsChecked) { return (Resolve-ImageVariant $DoroFramePath) }
        if ($CinderellaFrameCheck.IsChecked) { return (Resolve-ImageVariant $CinderellaFramePath) }
    }
    if ($CustomFrameCheck.IsChecked) { return Get-CustomFramePath }
    return $null
}

function Get-SelectedFrameLabel {
    if ($MarianFrameCheck.IsChecked) { return "玛丽安" }
    if ($DoroFrameCheck.IsChecked) { return "Doro" }
    if ($CinderellaFrameCheck.IsChecked) { return "灰姑娘" }
    if ($CustomFrameCheck.IsChecked) { return "自定义底图" }
    return $null
}

function Get-PostDataMode {
    if ($CurrentCaptureMode -eq "season") { return "detailed" }
    if ($GroupSimpleDataCheck.IsChecked) { return "simple" }
    if ($GroupDetailedDataCheck.IsChecked) { return "detailed" }
    return "none"
}

function Get-GroupCaptureOutputTitle([int]$GroupSize) {
    $postMode = Get-PostDataMode
    $allGroups = [bool]$GroupAllDataCheck.IsChecked
    if ($postMode -eq "simple") {
        if ($allGroups) {
            switch ($GroupSize) {
                8 { return "64进32全部战斗数据（简）" }
                4 { return "32进16全部战斗数据（简）" }
                2 { return "16进8全部战斗数据（简）" }
            }
        }
        switch ($GroupSize) {
            8 { return "64进32当前组8人战斗数据（简）" }
            4 { return "32进16当前组4人战斗数据（简）" }
            2 { return "16进8当前组双人战斗数据（简）" }
        }
    } elseif ($postMode -eq "detailed") {
        if ($allGroups) {
            switch ($GroupSize) {
                8 { return "64进32全部战斗数据（详）" }
                4 { return "32进16全部战斗数据（详）" }
                2 { return "16进8全部战斗数据（详）" }
            }
        }
        switch ($GroupSize) {
            8 { return "64进32当前组8人战斗数据（详）" }
            4 { return "32进16当前组4人战斗数据（详）" }
            2 { return "16进8当前组双人战斗数据（详）" }
        }
    }
    if ($allGroups) {
        switch ($GroupSize) {
            8 { return "64强全部GROUP阵容" }
            4 { return "32强全部GROUP阵容" }
            2 { return "16强全部GROUP双人阵容" }
        }
    }
    switch ($GroupSize) {
        8 { return "64强该组8人阵容" }
        4 { return "32强该组4人阵容" }
        2 { return "16强该组双人阵容" }
    }
    return "晋级赛GROUP阵容"
}

function Get-Top8CaptureOutputTitle([int]$GroupSize, [bool]$Top8Pyramid) {
    $postMode = Get-PostDataMode
    if ($Top8Pyramid) {
        if ($postMode -eq "simple") { return "TOP8-决赛战斗数据（简）" }
        if ($postMode -eq "detailed") { return "TOP8-决赛战斗数据（详）" }
        return "TOP8-决赛战斗数据"
    }
    if ($postMode -eq "simple") {
        switch ($GroupSize) {
            8 { return "8进4全部战斗数据（简）" }
            4 { return "4进2全部战斗数据（简）" }
            2 { return "决赛战斗数据（简）" }
        }
    } elseif ($postMode -eq "detailed") {
        switch ($GroupSize) {
            8 { return "8进4全部战斗数据（详）" }
            4 { return "4进2全部战斗数据（详）" }
            2 { return "决赛战斗数据（详）" }
        }
    }
    switch ($GroupSize) {
        8 { return "TOP8阵容" }
        4 { return "TOP4阵容" }
        2 { return "决赛阵容" }
    }
    return "TOP8阵容"
}

function Get-CaptureOutputTitle($GroupSize, [bool]$Top8Pyramid) {
    if ($CurrentCaptureMode -eq "support") { return "应援双方阵容" }
    if ($CurrentCaptureMode -eq "group") { return Get-GroupCaptureOutputTitle ([int]$GroupSize) }
    if ($CurrentCaptureMode -eq "top8") { return Get-Top8CaptureOutputTitle ([int]$GroupSize) $Top8Pyramid }
    if ($CurrentCaptureMode -eq "season") { return "64进32全部战斗数据（详）" }
    return "单人阵容"
}

function Get-CurrentDisplayResolutionLabel {
    try {
        $width = [NativeWin]::GetSystemMetrics([NativeWin]::SM_CXSCREEN)
        $height = [NativeWin]::GetSystemMetrics([NativeWin]::SM_CYSCREEN)
        if ($width -gt 0 -and $height -gt 0) {
            return ("{0}x{1}" -f $width, $height)
        }
    } catch {}
    return $null
}

function Get-UniqueOutputPath([string]$Directory, [string]$FileName) {
    $path = Join-Path $Directory $FileName
    if (-not (Test-Path $path)) { return $path }
    $stem = [IO.Path]::GetFileNameWithoutExtension($FileName)
    $extension = [IO.Path]::GetExtension($FileName)
    for ($index = 2; $index -lt 1000; $index++) {
        $candidate = Join-Path $Directory ("{0}-{1}{2}" -f $stem, $index, $extension)
        if (-not (Test-Path $candidate)) { return $candidate }
    }
    return (Join-Path $Directory ("{0}-{1}{2}" -f $stem, (Get-Date -Format "HHmmss"), $extension))
}

function Set-FrameBackgroundOptionsVisible([bool]$Visible) {
    $visibility = if ($Visible) { "Visible" } else { "Collapsed" }
    if ($FrameOptionsTitleText) { $FrameOptionsTitleText.Visibility = $visibility }
    if ($FrameOptionsGrid) { $FrameOptionsGrid.Visibility = $visibility }
    if ($GroupPostDataPanel) {
        $GroupPostDataPanel.Margin = if ($Visible) {
            [Windows.Thickness]::new(0, 8, 0, 0)
        } else {
            [Windows.Thickness]::new(0, 0, 0, 0)
        }
    }
    if (-not $Visible) {
        foreach ($option in @($MarianFrameCheck, $DoroFrameCheck, $CinderellaFrameCheck, $CustomFrameCheck)) {
            if ($option) { $option.IsChecked = $false }
        }
    }
}

function Set-PostDataControlsForMode([string]$Mode) {
    if ($Mode -eq "season") {
        $GroupSimpleDataCheck.Visibility = "Collapsed"
        $GroupSimpleDataCheck.IsChecked = $false
        $GroupSimpleDataCheck.IsEnabled = $false
        $GroupSimpleDataCheck.Opacity = 0.0
        $GroupDetailedDataCheck.Visibility = "Visible"
        $GroupDetailedDataCheck.IsChecked = $true
        $GroupDetailedDataCheck.IsEnabled = $false
        $GroupDetailedDataCheck.Opacity = 0.96
        return
    }
    $GroupSimpleDataCheck.Visibility = "Visible"
    $GroupSimpleDataCheck.IsEnabled = $true
    $GroupSimpleDataCheck.Opacity = 1.0
    $GroupDetailedDataCheck.Visibility = "Visible"
    $GroupDetailedDataCheck.IsEnabled = $true
    $GroupDetailedDataCheck.Opacity = 1.0
}

function Set-SubPageMode($Mode) {
    $script:CurrentCaptureMode = $Mode
    $OcrExecutePanel.Visibility = "Collapsed"
    $SeasonExecutePanel.Visibility = "Collapsed"
    $SubPageHelpText.Visibility = "Visible"
    Set-FrameBackgroundOptionsVisible $true
    if ($Mode -eq "support") {
        $SubPageHelpText.Text = $TextSupportHelp
        $ExampleImage.Source = New-Bitmap $SupportExamplePath
        $ExampleBorder.Visibility = "Visible"
        $SettingsPanel.Visibility = "Collapsed"
        $ExecuteButton.Visibility = "Visible"
        $GroupExecutePanel.Visibility = "Collapsed"
        $Top8ExecutePanel.Visibility = "Collapsed"
        $FrameOptionsPanel.Visibility = "Visible"
        $SupportStatusCheck.Visibility = "Visible"
        $GroupPostDataPanel.Visibility = "Collapsed"
        $GroupSimpleDataCheck.IsChecked = $false
        $GroupDetailedDataCheck.IsChecked = $false
        $GroupAllDataCheck.IsChecked = $false
        $ExportOcrDataCheck.IsChecked = $false
        $CustomFrameTooltipText.Text = $TextCustomSupportTip
    } elseif ($Mode -eq "group") {
        $SubPageHelpText.Text = $TextGroupHelp
        $ExampleImage.Source = New-Bitmap $GroupExamplePath
        $ExampleBorder.Visibility = "Visible"
        $SettingsPanel.Visibility = "Collapsed"
        $ExecuteButton.Visibility = "Collapsed"
        $GroupExecutePanel.Visibility = "Visible"
        $Top8ExecutePanel.Visibility = "Collapsed"
        $FrameOptionsPanel.Visibility = "Visible"
        Set-FrameBackgroundOptionsVisible $false
        $SupportStatusCheck.Visibility = "Collapsed"
        $SupportStatusCheck.IsChecked = $false
        $GroupPostDataPanel.Visibility = "Visible"
        $GroupPostDataHelpText.Visibility = "Visible"
        $GroupAllDataCheck.Visibility = "Visible"
        Set-PostDataControlsForMode "group"
        $CustomFrameTooltipText.Text = $TextCustomGroupTip
    } elseif ($Mode -eq "top8") {
        $SubPageHelpText.Text = $TextTop8Help
        $ExampleImage.Source = New-Bitmap (Resolve-OptionalImage $Top8ExamplePath $GroupExamplePath)
        $ExampleBorder.Visibility = "Visible"
        $SettingsPanel.Visibility = "Collapsed"
        $ExecuteButton.Visibility = "Collapsed"
        $GroupExecutePanel.Visibility = "Collapsed"
        $Top8ExecutePanel.Visibility = "Visible"
        $FrameOptionsPanel.Visibility = "Visible"
        $SupportStatusCheck.Visibility = "Collapsed"
        $SupportStatusCheck.IsChecked = $false
        $GroupPostDataPanel.Visibility = "Visible"
        $GroupPostDataHelpText.Visibility = "Collapsed"
        $GroupAllDataCheck.Visibility = "Collapsed"
        $GroupAllDataCheck.IsChecked = $false
        Set-PostDataControlsForMode "top8"
        $CustomFrameTooltipText.Text = $TextCustomGroupTip
    } elseif ($Mode -eq "season") {
        $SubPageHelpText.Text = $TextSeasonHelp
        $ExampleImage.Source = New-Bitmap $GroupExamplePath
        $ExampleBorder.Visibility = "Visible"
        $SettingsPanel.Visibility = "Collapsed"
        $ExecuteButton.Visibility = "Collapsed"
        $GroupExecutePanel.Visibility = "Collapsed"
        $Top8ExecutePanel.Visibility = "Collapsed"
        $SeasonExecutePanel.Visibility = "Visible"
        $FrameOptionsPanel.Visibility = "Visible"
        Set-FrameBackgroundOptionsVisible $false
        $SupportStatusCheck.Visibility = "Collapsed"
        $SupportStatusCheck.IsChecked = $false
        $GroupPostDataPanel.Visibility = "Visible"
        $GroupPostDataHelpText.Visibility = "Collapsed"
        $GroupAllDataCheck.Visibility = "Collapsed"
        $GroupAllDataCheck.IsChecked = $false
        Set-PostDataControlsForMode "season"
        $CustomFrameTooltipText.Text = $TextCustomSeasonTip
    } elseif ($Mode -eq "settings") {
        $SubPageHelpText.Text = $TextSettingsHelp
        $ExampleBorder.Visibility = "Collapsed"
        $SettingsPanel.Visibility = "Visible"
        $ExecuteButton.Visibility = "Collapsed"
        $GroupExecutePanel.Visibility = "Collapsed"
        $Top8ExecutePanel.Visibility = "Collapsed"
        $FrameOptionsPanel.Visibility = "Collapsed"
        $SupportStatusCheck.Visibility = "Collapsed"
        $SupportStatusCheck.IsChecked = $false
        $GroupPostDataPanel.Visibility = "Collapsed"
        $GroupSimpleDataCheck.IsChecked = $false
        $GroupDetailedDataCheck.IsChecked = $false
        $GroupAllDataCheck.IsChecked = $false
        $ExportOcrDataCheck.IsChecked = $false
    } elseif ($Mode -eq "ocr") {
        $SubPageHelpText.Text = $TextOcrHelp
        $SubPageHelpText.Visibility = "Collapsed"
        $ExampleBorder.Visibility = "Collapsed"
        $SettingsPanel.Visibility = "Collapsed"
        $ExecuteButton.Visibility = "Collapsed"
        $GroupExecutePanel.Visibility = "Collapsed"
        $Top8ExecutePanel.Visibility = "Collapsed"
        $OcrExecutePanel.Visibility = "Visible"
        $FrameOptionsPanel.Visibility = "Collapsed"
        $SupportStatusCheck.Visibility = "Collapsed"
        $SupportStatusCheck.IsChecked = $false
        $GroupPostDataPanel.Visibility = "Collapsed"
        $GroupSimpleDataCheck.IsChecked = $false
        $GroupDetailedDataCheck.IsChecked = $false
        $GroupAllDataCheck.IsChecked = $false
        $ExportOcrDataCheck.IsChecked = $false
        Update-OcrSelectedPath
        Update-OcrSeasonSlotStatuses
    } else {
        $SubPageHelpText.Text = $TextArenaHelp
        $ExampleImage.Source = New-Bitmap $ExamplePath
        $ExampleBorder.Visibility = "Visible"
        $SettingsPanel.Visibility = "Collapsed"
        $ExecuteButton.Visibility = "Visible"
        $GroupExecutePanel.Visibility = "Collapsed"
        $Top8ExecutePanel.Visibility = "Collapsed"
        $FrameOptionsPanel.Visibility = "Visible"
        $SupportStatusCheck.Visibility = "Collapsed"
        $SupportStatusCheck.IsChecked = $false
        $GroupPostDataPanel.Visibility = "Collapsed"
        $GroupSimpleDataCheck.IsChecked = $false
        $GroupDetailedDataCheck.IsChecked = $false
        $GroupAllDataCheck.IsChecked = $false
        $ExportOcrDataCheck.IsChecked = $false
        $CustomFrameTooltipText.Text = $TextCustomSingleTip
    }
    Update-ModeButtonStyles
}

function Show-SubPage {
    $SubPagePanel.Visibility = "Visible"
    $BrandBlock.Visibility = "Collapsed"
    if ($SiteLinksPanel) { $SiteLinksPanel.Visibility = "Collapsed" }
}

function Hide-SubPage {
    $SubPagePanel.Visibility = "Collapsed"
    $BrandBlock.Visibility = "Visible"
    if ($SiteLinksPanel) { $SiteLinksPanel.Visibility = "Visible" }
}

$ArenaButton.Add_Click({
    Set-SubPageMode "single"
    Show-SubPage
})

$SupportButton.Add_Click({
    Set-SubPageMode "support"
    Show-SubPage
})

$GroupButton.Add_Click({
    Set-SubPageMode "group"
    Show-SubPage
})

$Top8Button.Add_Click({
    Set-SubPageMode "top8"
    Show-SubPage
})

$SeasonCaptureButton.Add_Click({
    Set-SubPageMode "season"
    Show-SubPage
})

$NikkeNameListButton.Add_Click({
    Show-NikkeNameManager
})

$PostDataOcrButton.Add_Click({
    Set-SubPageMode "ocr"
    Show-SubPage
})

$BackButton.Add_Click({
    Hide-SubPage
})

$FolderButton.Add_Click({
    Start-Process -FilePath $OutputRoot
})

$SettingsButton.Add_Click({
    Set-SubPageMode "settings"
    Show-SubPage
})

function Refresh-Ui {
    $Window.Dispatcher.Invoke(
        [Action]{},
        [Windows.Threading.DispatcherPriority]::Background
    )
}

function Show-TopMessage($Message, $Title, $Icon) {
    $previousTopmost = $Window.Topmost
    try {
        $Window.WindowState = "Normal"
        $Window.Show()
        $Window.Topmost = $true
        $Window.Activate() | Out-Null
        [System.Windows.MessageBox]::Show(
            $Window,
            $Message,
            $Title,
            [System.Windows.MessageBoxButton]::OK,
            $Icon
        ) | Out-Null
    } finally {
        $Window.Topmost = $previousTopmost
    }
}

$script:OcrProgressWindow = $null
$script:OcrProgressBar = $null
$script:OcrProgressDetailText = $null
$script:OcrProgressThermalText = $null
$script:OcrProgressCloseButton = $null
$script:OcrProgressStopButton = $null
$script:OcrProgressAllowStop = $false
$script:OcrProgressOpenLogButton = $null
$script:OcrProgressOpenDataFolderButton = $null
$script:OcrProgressBorder = $null
$script:OcrProgressTitleText = $null
$script:OcrProgressMessageText = $null
$script:OcrProgressLogBox = $null
$script:OcrProgressLogPath = $null
$script:OcrProgressOutputFolder = $null
$script:OcrProgressStartedAt = $null
$script:OcrProgressLastPrefix = $null
$script:OcrProgressLastPercent = $null

function New-WpfBrush($Color) {
    return (New-Object Windows.Media.BrushConverter).ConvertFromString($Color)
}

function Get-OcrProgressPalette {
    if ($script:CurrentTheme -eq "pink") {
        return @{
            Window = "#00FFFFFF"
            Panel = "#F8FFF7FC"
            Border = "#FFFFB8D4"
            Accent = "#FFFF8FBE"
            Text = "#FF5E2F45"
            Muted = "#FF9A5D77"
            Button = "#FFFFDCEB"
        }
    }
    return @{
        Window = "#00000000"
        Panel = "#F30B1628"
        Border = "#885EDCFF"
        Accent = "#FF6BE6FF"
        Text = "#FFF7FBFF"
        Muted = "#FFBCD2E5"
        Button = "#FF17314C"
    }
}

function Set-OcrProgressWindowTheme {
    if (-not $script:OcrProgressWindow) { return }
    $palette = Get-OcrProgressPalette
    $script:OcrProgressWindow.Background = New-WpfBrush $palette.Window
    if ($script:OcrProgressBorder) {
        $script:OcrProgressBorder.Background = New-WpfBrush $palette.Panel
        $script:OcrProgressBorder.BorderBrush = New-WpfBrush $palette.Border
    }
    if ($script:OcrProgressTitleText) { $script:OcrProgressTitleText.Foreground = New-WpfBrush $palette.Text }
    if ($script:OcrProgressMessageText) { $script:OcrProgressMessageText.Foreground = New-WpfBrush $palette.Text }
    if ($script:OcrProgressDetailText) { $script:OcrProgressDetailText.Foreground = New-WpfBrush $palette.Muted }
    if ($script:OcrProgressThermalText) { $script:OcrProgressThermalText.Foreground = New-WpfBrush $palette.Muted }
    if ($script:OcrProgressBar) { $script:OcrProgressBar.Foreground = New-WpfBrush $palette.Accent }
    if ($script:OcrProgressStopButton) {
        $script:OcrProgressStopButton.Background = New-WpfBrush $palette.Button
        $script:OcrProgressStopButton.BorderBrush = New-WpfBrush $palette.Border
        $script:OcrProgressStopButton.Foreground = New-WpfBrush $palette.Text
    }
    if ($script:OcrProgressCloseButton) {
        $script:OcrProgressCloseButton.Background = New-WpfBrush $palette.Button
        $script:OcrProgressCloseButton.BorderBrush = New-WpfBrush $palette.Border
        $script:OcrProgressCloseButton.Foreground = New-WpfBrush $palette.Text
    }
    if ($script:OcrProgressOpenLogButton) {
        $script:OcrProgressOpenLogButton.Background = New-WpfBrush $palette.Button
        $script:OcrProgressOpenLogButton.BorderBrush = New-WpfBrush $palette.Border
        $script:OcrProgressOpenLogButton.Foreground = New-WpfBrush $palette.Text
    }
    if ($script:OcrProgressOpenDataFolderButton) {
        $script:OcrProgressOpenDataFolderButton.Background = New-WpfBrush $palette.Button
        $script:OcrProgressOpenDataFolderButton.BorderBrush = New-WpfBrush $palette.Border
        $script:OcrProgressOpenDataFolderButton.Foreground = New-WpfBrush $palette.Text
    }
    if ($script:OcrProgressLogBox) {
        $script:OcrProgressLogBox.Background = New-WpfBrush $palette.Window
        $script:OcrProgressLogBox.BorderBrush = New-WpfBrush $palette.Border
        $script:OcrProgressLogBox.Foreground = New-WpfBrush $palette.Muted
    }
}

function Close-OcrProgressWindow {
    if ($script:OcrProgressWindow) {
        try { $script:OcrProgressWindow.Close() } catch {}
    }
    $script:OcrProgressWindow = $null
    $script:OcrProgressBar = $null
    $script:OcrProgressDetailText = $null
    $script:OcrProgressThermalText = $null
    $script:OcrProgressCloseButton = $null
    $script:OcrProgressStopButton = $null
    $script:OcrProgressAllowStop = $false
    $script:OcrProgressOpenLogButton = $null
    $script:OcrProgressOpenDataFolderButton = $null
    $script:OcrProgressBorder = $null
    $script:OcrProgressTitleText = $null
    $script:OcrProgressMessageText = $null
    $script:OcrProgressLogBox = $null
    $script:OcrProgressLogPath = $null
    $script:OcrProgressOutputFolder = $null
    $script:OcrProgressStartedAt = $null
    $script:OcrProgressLastPrefix = $null
    $script:OcrProgressLastPercent = $null
}

function Open-OcrProgressLog {
    if (-not $script:OcrProgressLogPath -or -not (Test-Path $script:OcrProgressLogPath)) { return }
    try {
        Start-Process -FilePath "notepad.exe" -ArgumentList @($script:OcrProgressLogPath)
    } catch {
        try { Invoke-Item -LiteralPath $script:OcrProgressLogPath } catch {}
    }
}

function Open-OcrOutputFolder {
    $folder = $script:OcrProgressOutputFolder
    if (-not $folder -or -not (Test-Path $folder)) {
        $folder = Get-OutputDateFolder
    }
    try {
        Start-Process -FilePath $folder
    } catch {
        try { Invoke-Item -LiteralPath $folder } catch {}
    }
}

function Add-OcrProgressLogLine($Line) {
    if ([string]::IsNullOrWhiteSpace($Line)) { return }
    if (-not $script:OcrProgressLogBox) { return }
    $text = [string]$Line
    if ($script:OcrProgressLogBox.Text.Length -gt 50000) {
        $script:OcrProgressLogBox.Text = $script:OcrProgressLogBox.Text.Substring([Math]::Max(0, $script:OcrProgressLogBox.Text.Length - 30000))
    }
    $script:OcrProgressLogBox.AppendText($text + [Environment]::NewLine)
    $script:OcrProgressLogBox.ScrollToEnd()
}

function New-OcrRunLogFilePath {
    $folder = Get-OutputDateFolder
    return (Join-Path $folder ("ocr_run_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss")))
}

function Initialize-OcrRunLog($Path, $Title, $Arguments) {
    if (-not $Path) { return }
    try {
        $pythonForLog = if ($script:ActiveOcrPythonExe) { $script:ActiveOcrPythonExe } else { $OcrPythonExe }
        $lines = @(
            ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Title),
            ("python: {0}" -f $pythonForLog),
            ("arguments: {0}" -f $Arguments),
            ""
        )
        $encoding = [Text.UTF8Encoding]::new($true)
        [IO.File]::WriteAllLines($Path, [string[]]$lines, $encoding)
    } catch {}
}

function Add-OcrRunLogLine($Path, $Line) {
    if (-not $Path -or [string]::IsNullOrWhiteSpace($Line)) { return }
    try {
        $encoding = [Text.UTF8Encoding]::new($true)
        [IO.File]::AppendAllText($Path, ([string]$Line + [Environment]::NewLine), $encoding)
    } catch {}
}

function Apply-OcrEncodingEnvironment($ProcessStartInfo) {
    if (-not $ProcessStartInfo) { return }
    $ProcessStartInfo.EnvironmentVariables["PYTHONUTF8"] = "1"
    $ProcessStartInfo.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
    if ($OcrGpuPythonExe -and $ProcessStartInfo.FileName -eq $OcrGpuPythonExe) {
        $gpuRoot = Split-Path -Parent (Split-Path -Parent $OcrGpuPythonExe)
        $gpuDllDirs = @(
            Join-Path $gpuRoot "Lib\site-packages\nvidia\cuda_runtime\bin"
            Join-Path $gpuRoot "Lib\site-packages\nvidia\cublas\bin"
            Join-Path $gpuRoot "Lib\site-packages\nvidia\cuda_nvrtc\bin"
            Join-Path $gpuRoot "Lib\site-packages\nvidia\cudnn\bin"
        ) | Where-Object { Test-Path $_ }
        if ($gpuDllDirs.Count -gt 0) {
            $existingPath = $ProcessStartInfo.EnvironmentVariables["PATH"]
            $ProcessStartInfo.EnvironmentVariables["PATH"] = (($gpuDllDirs + @($existingPath)) -join ";")
        }
    }
}

function Drain-OcrProcessLogQueue($Queue, $Path, $CapturedLines) {
    if (-not $Queue) { return }
    $line = $null
    while ($Queue.TryDequeue([ref]$line)) {
        if (-not [string]::IsNullOrWhiteSpace($line)) {
            if ($null -ne $CapturedLines) { [void]$CapturedLines.Add([string]$line) }
            Add-OcrProgressLogLine $line
            Add-OcrRunLogLine $Path $line
        }
        $line = $null
    }
}

function Drain-OcrReaderTask($TaskRef, $Reader, $Prefix, $Path, $CapturedLines) {
    if (-not $TaskRef -or -not $TaskRef.Value) { return }
    $task = $TaskRef.Value
    while ($task -and $task.IsCompleted) {
        try {
            $line = $task.Result
        } catch {
            $TaskRef.Value = $null
            return
        }
        if ($null -eq $line) {
            $TaskRef.Value = $null
            return
        }
        $text = $Prefix + $line
        if ($null -ne $CapturedLines) { [void]$CapturedLines.Add($text) }
        Add-OcrProgressLogLine $text
        Add-OcrRunLogLine $Path $text
        $task = $Reader.ReadLineAsync()
        $TaskRef.Value = $task
    }
}

function Drain-OcrProcessOutput($StdoutTaskRef, $StderrTaskRef, $Process, $Path, $CapturedLines) {
    if (-not $Process) { return }
    Drain-OcrReaderTask $StdoutTaskRef $Process.StandardOutput "[stdout] " $Path $CapturedLines
    Drain-OcrReaderTask $StderrTaskRef $Process.StandardError "[stderr] " $Path $CapturedLines
}

function Complete-OcrProcessOutput($StdoutTaskRef, $StderrTaskRef, $Process, $Path, $CapturedLines) {
    for ($index = 0; $index -lt 20; $index++) {
        Drain-OcrProcessOutput $StdoutTaskRef $StderrTaskRef $Process $Path $CapturedLines
        if ((-not $StdoutTaskRef.Value) -and (-not $StderrTaskRef.Value)) { return }
        Start-Sleep -Milliseconds 50
    }
}

function Show-OcrProgressWindow($Message, $RunLogPath = $null, [bool]$AllowStop = $false) {
    if ($RunLogPath) { $script:OcrProgressLogPath = $RunLogPath }
    $script:OcrProgressStartedAt = Get-Date
    $script:OcrProgressLastPrefix = $null
    $script:OcrProgressLastPercent = $null
    $script:OcrProgressAllowStop = [bool]$AllowStop

    if ($script:OcrProgressWindow) {
        $script:OcrProgressWindow.Title = $TextAutoOcrStartTitle
        if ($script:OcrProgressTitleText) { $script:OcrProgressTitleText.Text = $TextAutoOcrStartTitle }
        if ($script:OcrProgressMessageText) { $script:OcrProgressMessageText.Text = $Message }
        if ($script:OcrProgressMessageText) { $script:OcrProgressMessageText.Visibility = "Visible" }
        if ($script:OcrProgressDetailText) { $script:OcrProgressDetailText.Text = "OCR 引擎启动中..." }
        if ($script:OcrProgressThermalText) { $script:OcrProgressThermalText.Text = "" }
        if ($script:OcrProgressLogBox) { $script:OcrProgressLogBox.Text = "" }
        if ($script:OcrProgressBar) {
            $script:OcrProgressBar.IsIndeterminate = $true
            $script:OcrProgressBar.Value = 0
        }
        if ($script:OcrProgressCloseButton) { $script:OcrProgressCloseButton.Visibility = "Collapsed" }
        if ($script:OcrProgressStopButton) {
            $script:OcrProgressStopButton.Visibility = if ($script:OcrProgressAllowStop) { "Visible" } else { "Collapsed" }
            $script:OcrProgressStopButton.IsEnabled = $true
        }
        if ($script:OcrProgressOpenLogButton) { $script:OcrProgressOpenLogButton.Visibility = "Collapsed" }
        if ($script:OcrProgressOpenDataFolderButton) { $script:OcrProgressOpenDataFolderButton.Visibility = "Collapsed" }
        Set-OcrProgressWindowTheme
        $script:OcrProgressWindow.Show()
        Refresh-Ui
        return
    }

    $progressWindow = New-Object Windows.Window
    $progressWindow.Title = $TextAutoOcrStartTitle
    $progressWindow.Width = 660
    $progressWindow.Height = 440
    $progressWindow.ResizeMode = "NoResize"
    $progressWindow.WindowStartupLocation = "CenterOwner"
    $progressWindow.WindowStyle = "None"
    $progressWindow.AllowsTransparency = $true
    $progressWindow.ShowInTaskbar = $false
    $progressWindow.Topmost = $false
    $progressWindow.ShowActivated = $false
    try { $progressWindow.Owner = $Window } catch {}

    $border = New-Object Windows.Controls.Border
    $border.CornerRadius = [Windows.CornerRadius]::new(10)
    $border.BorderThickness = [Windows.Thickness]::new(1)
    $border.Padding = [Windows.Thickness]::new(24)
    $progressWindow.Content = $border

    $stack = New-Object Windows.Controls.StackPanel
    $border.Child = $stack

    $title = New-Object Windows.Controls.TextBlock
    $title.Text = $TextAutoOcrStartTitle
    $title.FontSize = 22
    $title.FontWeight = "SemiBold"
    $title.Margin = [Windows.Thickness]::new(0, 0, 0, 10)
    $stack.Children.Add($title) | Out-Null

    $messageText = New-Object Windows.Controls.TextBlock
    $messageText.Text = $Message
    $messageText.FontSize = 14
    $messageText.TextWrapping = "Wrap"
    $messageText.LineHeight = 22
    $messageText.Margin = [Windows.Thickness]::new(0, 0, 0, 16)
    $stack.Children.Add($messageText) | Out-Null

    $detail = New-Object Windows.Controls.TextBlock
    $detail.Text = "OCR 引擎启动中..."
    $detail.FontSize = 12
    $detail.TextWrapping = "Wrap"
    $detail.Margin = [Windows.Thickness]::new(0, 0, 0, 10)
    $stack.Children.Add($detail) | Out-Null

    $thermalText = New-Object Windows.Controls.TextBlock
    $thermalText.Text = ""
    $thermalText.FontSize = 11
    $thermalText.TextWrapping = "Wrap"
    $thermalText.Margin = [Windows.Thickness]::new(0, 0, 0, 10)
    $stack.Children.Add($thermalText) | Out-Null

    $bar = New-Object Windows.Controls.ProgressBar
    $bar.Height = 8
    $bar.Minimum = 0
    $bar.Maximum = 100
    $bar.IsIndeterminate = $true
    $bar.Margin = [Windows.Thickness]::new(0, 0, 0, 18)
    $stack.Children.Add($bar) | Out-Null

    $logBox = New-Object Windows.Controls.TextBox
    $logBox.Height = 150
    $logBox.FontFamily = "Microsoft YaHei UI"
    $logBox.FontSize = 11
    $logBox.IsReadOnly = $true
    $logBox.TextWrapping = "NoWrap"
    $logBox.AcceptsReturn = $true
    $logBox.VerticalScrollBarVisibility = "Auto"
    $logBox.HorizontalScrollBarVisibility = "Auto"
    $logBox.Margin = [Windows.Thickness]::new(0, 0, 0, 14)
    $stack.Children.Add($logBox) | Out-Null

    $buttonPanel = New-Object Windows.Controls.StackPanel
    $buttonPanel.Orientation = "Horizontal"
    $buttonPanel.HorizontalAlignment = "Right"
    $stack.Children.Add($buttonPanel) | Out-Null

    $stopButton = New-Object Windows.Controls.Button
    $stopButton.Content = "终止任务"
    $stopButton.Width = 104
    $stopButton.Height = 34
    $stopButton.Margin = [Windows.Thickness]::new(0, 0, 10, 0)
    $stopButton.Visibility = if ($script:OcrProgressAllowStop) { "Visible" } else { "Collapsed" }
    $stopButton.Cursor = "Hand"
    $stopButton.Add_Click({ Request-OcrRecognitionStop })
    $buttonPanel.Children.Add($stopButton) | Out-Null

    $openLogButton = New-Object Windows.Controls.Button
    $openLogButton.Content = "打开日志"
    $openLogButton.Width = 110
    $openLogButton.Height = 34
    $openLogButton.Margin = [Windows.Thickness]::new(0, 0, 10, 0)
    $openLogButton.Visibility = "Collapsed"
    $openLogButton.Cursor = "Hand"
    $openLogButton.Add_Click({ Open-OcrProgressLog })
    $buttonPanel.Children.Add($openLogButton) | Out-Null

    $openDataFolderButton = New-Object Windows.Controls.Button
    $openDataFolderButton.Content = "打开数据文件夹"
    $openDataFolderButton.Width = 132
    $openDataFolderButton.Height = 34
    $openDataFolderButton.Margin = [Windows.Thickness]::new(0, 0, 10, 0)
    $openDataFolderButton.Visibility = "Collapsed"
    $openDataFolderButton.Cursor = "Hand"
    $openDataFolderButton.Add_Click({ Open-OcrOutputFolder })
    $buttonPanel.Children.Add($openDataFolderButton) | Out-Null

    $button = New-Object Windows.Controls.Button
    $button.Content = $TextDoneTitle
    $button.Width = 96
    $button.Height = 34
    $button.HorizontalAlignment = "Right"
    $button.Visibility = "Collapsed"
    $button.Cursor = "Hand"
    $button.Add_Click({ Close-OcrProgressWindow })
    $buttonPanel.Children.Add($button) | Out-Null

    $progressWindow.Add_Closed({
        $script:OcrProgressWindow = $null
        $script:OcrProgressBar = $null
        $script:OcrProgressDetailText = $null
        $script:OcrProgressThermalText = $null
        $script:OcrProgressCloseButton = $null
        $script:OcrProgressStopButton = $null
        $script:OcrProgressAllowStop = $false
        $script:OcrProgressOpenLogButton = $null
        $script:OcrProgressOpenDataFolderButton = $null
        $script:OcrProgressBorder = $null
        $script:OcrProgressTitleText = $null
        $script:OcrProgressMessageText = $null
        $script:OcrProgressLogBox = $null
        $script:OcrProgressLogPath = $null
        $script:OcrProgressOutputFolder = $null
        $script:OcrProgressStartedAt = $null
        $script:OcrProgressLastPrefix = $null
        $script:OcrProgressLastPercent = $null
    })

    $script:OcrProgressWindow = $progressWindow
    $script:OcrProgressBar = $bar
    $script:OcrProgressDetailText = $detail
    $script:OcrProgressThermalText = $thermalText
    $script:OcrProgressCloseButton = $button
    $script:OcrProgressStopButton = $stopButton
    $script:OcrProgressOpenLogButton = $openLogButton
    $script:OcrProgressOpenDataFolderButton = $openDataFolderButton
    $script:OcrProgressBorder = $border
    $script:OcrProgressTitleText = $title
    $script:OcrProgressMessageText = $messageText
    $script:OcrProgressLogBox = $logBox
    Set-OcrProgressWindowTheme
    $progressWindow.Show()
    Refresh-Ui
}

function Update-OcrProgressWindow($Text, $Percent = $null) {
    if (-not $script:OcrProgressWindow) { return }
    if ($script:OcrProgressDetailText) { $script:OcrProgressDetailText.Text = $Text }
    if ($null -ne $Percent -and $script:OcrProgressBar) {
        $value = [Math]::Max(0, [Math]::Min(100, [double]$Percent))
        $script:OcrProgressBar.IsIndeterminate = $false
        $script:OcrProgressBar.Value = $value
    }
    Refresh-Ui
}

function Update-OcrThermalProgressText($Text) {
    if (-not $script:OcrProgressThermalText) { return }
    $script:OcrProgressThermalText.Text = [string]$Text
}

function Format-OcrMetricValue($Value, $Suffix = "") {
    if ($null -eq $Value) { return "无法读取" }
    try {
        $number = [double]$Value
        if ([double]::IsNaN($number) -or [double]::IsInfinity($number)) { return "无法读取" }
        return ($number.ToString("0", [Globalization.CultureInfo]::InvariantCulture) + $Suffix)
    } catch {
        return "无法读取"
    }
}

function Get-OcrCpuUsagePercent {
    try {
        $item = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'" -ErrorAction Stop
        if ($null -ne $item.PercentProcessorTime) { return [double]$item.PercentProcessorTime }
    } catch {}
    try {
        $counter = Get-Counter '\Processor(_Total)\% Processor Time' -ErrorAction Stop
        return [double]$counter.CounterSamples[0].CookedValue
    } catch {}
    return $null
}

function Get-OcrMemoryUsagePercent {
    try {
        $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
        $total = [double]$os.TotalVisibleMemorySize
        $free = [double]$os.FreePhysicalMemory
        if ($total -gt 0) {
            return (($total - $free) / $total) * 100.0
        }
    } catch {}
    return $null
}

function Resolve-OcrNvidiaSmiPath {
    if ($script:OcrNvidiaSmiResolved) { return $script:OcrNvidiaSmiPath }
    $script:OcrNvidiaSmiResolved = $true
    $candidates = @()
    $command = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source) { $candidates += $command.Source }
    if ($env:ProgramFiles) { $candidates += (Join-Path $env:ProgramFiles "NVIDIA Corporation\NVSMI\nvidia-smi.exe") }
    if (${env:ProgramFiles(x86)}) { $candidates += (Join-Path ${env:ProgramFiles(x86)} "NVIDIA Corporation\NVSMI\nvidia-smi.exe") }
    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        if (Test-Path $candidate) {
            $script:OcrNvidiaSmiPath = $candidate
            return $candidate
        }
    }
    return $null
}

function Get-OcrGpuStatus {
    $path = Resolve-OcrNvidiaSmiPath
    if (-not $path) { return $null }
    try {
        $output = & $path --query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>$null | Select-Object -First 1
        if ([string]::IsNullOrWhiteSpace($output)) { return $null }
        $parts = @($output -split "," | ForEach-Object { $_.Trim() })
        if ($parts.Count -lt 4) { return $null }
        return [pscustomobject]@{
            Temp = [double]$parts[0]
            Util = [double]$parts[1]
            MemUsed = [double]$parts[2]
            MemTotal = [double]$parts[3]
        }
    } catch {
        return $null
    }
}

function Initialize-OcrHardwareMonitor {
    if ($script:OcrHardwareMonitorInitialized) { return $script:OcrHardwareMonitorAvailable }
    $script:OcrHardwareMonitorInitialized = $true
    $script:OcrHardwareMonitorAvailable = $false
    $script:OcrHardwareMonitorError = $null
    if (-not (Test-Path $script:OcrHardwareMonitorLibPath)) {
        $script:OcrHardwareMonitorError = "LibreHardwareMonitorLib.dll not found"
        return $false
    }
    try {
        if (Test-Path $script:OcrHidSharpLibPath) {
            Add-Type -Path $script:OcrHidSharpLibPath
        }
        Add-Type -Path $script:OcrHardwareMonitorLibPath
        $computer = New-Object LibreHardwareMonitor.Hardware.Computer
        $computer.IsCpuEnabled = $true
        $computer.IsGpuEnabled = $true
        $computer.IsMotherboardEnabled = $true
        $computer.Open()
        $script:OcrHardwareMonitor = $computer
        $script:OcrHardwareMonitorAvailable = $true
        return $true
    } catch {
        $script:OcrHardwareMonitorError = $_.Exception.Message
        $script:OcrHardwareMonitor = $null
        return $false
    }
}

function Close-OcrHardwareMonitor {
    if ($script:OcrHardwareMonitor) {
        try { $script:OcrHardwareMonitor.Close() } catch {}
    }
    $script:OcrHardwareMonitor = $null
    $script:OcrHardwareMonitorInitialized = $false
    $script:OcrHardwareMonitorAvailable = $false
}

function Get-OcrHardwareSensorReadings($Hardware) {
    $items = @()
    if (-not $Hardware) { return $items }
    try { $Hardware.Update() } catch {}
    try {
        foreach ($sensor in $Hardware.Sensors) {
            if ($sensor.SensorType -eq [LibreHardwareMonitor.Hardware.SensorType]::Temperature -and $null -ne $sensor.Value) {
                $items += [pscustomobject]@{
                    HardwareType = [string]$Hardware.HardwareType
                    HardwareName = [string]$Hardware.Name
                    SensorName = [string]$sensor.Name
                    Value = [double]$sensor.Value
                }
            }
        }
    } catch {}
    try {
        foreach ($subHardware in $Hardware.SubHardware) {
            $items += Get-OcrHardwareSensorReadings $subHardware
        }
    } catch {}
    return $items
}

function Select-OcrCpuTemperature($Readings) {
    $cpuReadings = @($Readings | Where-Object {
        $_.HardwareType -eq "Cpu" -and
        $_.SensorName -notmatch "Distance" -and
        $_.Value -gt 0
    })
    if (-not $cpuReadings -or $cpuReadings.Count -eq 0) { return $null }
    foreach ($preferred in @("CPU Package", "Core Max", "Core Average")) {
        $match = $cpuReadings | Where-Object { $_.SensorName -eq $preferred } | Select-Object -First 1
        if ($match) { return [double]$match.Value }
    }
    return [double](($cpuReadings | Sort-Object Value -Descending | Select-Object -First 1).Value)
}

function Select-OcrGpuTemperature($Readings) {
    $gpuReadings = @($Readings | Where-Object {
        $_.HardwareType -like "Gpu*" -and
        $_.SensorName -notmatch "Memory Junction|Hot Spot" -and
        $_.Value -gt 0
    })
    if (-not $gpuReadings -or $gpuReadings.Count -eq 0) { return $null }
    $core = $gpuReadings | Where-Object { $_.SensorName -eq "GPU Core" } | Select-Object -First 1
    if ($core) { return [double]$core.Value }
    return [double](($gpuReadings | Sort-Object Value -Descending | Select-Object -First 1).Value)
}

function Get-OcrHardwareTemperatures {
    if (-not (Initialize-OcrHardwareMonitor)) {
        return [pscustomobject]@{ CpuTemp = $null; GpuTemp = $null; Available = $false }
    }
    try {
        $readings = @()
        foreach ($hardware in $script:OcrHardwareMonitor.Hardware) {
            $readings += Get-OcrHardwareSensorReadings $hardware
        }
        return [pscustomobject]@{
            CpuTemp = Select-OcrCpuTemperature $readings
            GpuTemp = Select-OcrGpuTemperature $readings
            Available = $true
        }
    } catch {
        return [pscustomobject]@{ CpuTemp = $null; GpuTemp = $null; Available = $false }
    }
}

function Get-OcrResourceStatus {
    $cpuUsage = Get-OcrCpuUsagePercent
    $memoryUsage = Get-OcrMemoryUsagePercent
    $gpu = Get-OcrGpuStatus
    $hardwareTemps = Get-OcrHardwareTemperatures

    $cpuText = Format-OcrMetricValue $cpuUsage "%"
    $memoryText = Format-OcrMetricValue $memoryUsage "%"
    $cpuTempValue = $hardwareTemps.CpuTemp
    $gpuTempValue = $hardwareTemps.GpuTemp
    if ($gpu) {
        if ($null -ne $gpu.Temp) { $gpuTempValue = $gpu.Temp }
        $gpuUtilText = Format-OcrMetricValue $gpu.Util "%"
        $gpuMemoryText = ("{0} / {1} MB" -f (Format-OcrMetricValue $gpu.MemUsed ""), (Format-OcrMetricValue $gpu.MemTotal ""))
        $gpuUtilValue = $gpu.Util
        $gpuMemUsedValue = $gpu.MemUsed
        $gpuMemTotalValue = $gpu.MemTotal
    } else {
        $gpuUtilText = "无法读取"
        $gpuMemoryText = "无法读取"
        $gpuUtilValue = $null
        $gpuMemUsedValue = $null
        $gpuMemTotalValue = $null
    }

    $cpuTempText = Format-OcrMetricValue $cpuTempValue "°C"
    $gpuTempText = Format-OcrMetricValue $gpuTempValue "°C"
    $text = "CPU {0}，内存 {1}，CPU温度 {2}，GPU温度 {3}，GPU {4}，显存 {5}" -f $cpuText, $memoryText, $cpuTempText, $gpuTempText, $gpuUtilText, $gpuMemoryText

    return [pscustomobject]@{
        CpuUsage = $cpuUsage
        MemoryUsage = $memoryUsage
        CpuTemp = $cpuTempValue
        GpuTemp = $gpuTempValue
        GpuUtil = $gpuUtilValue
        GpuMemUsed = $gpuMemUsedValue
        GpuMemTotal = $gpuMemTotalValue
        Text = $text
    }
}

function Get-OcrResourceStatusText {
    return (Get-OcrResourceStatus).Text
}

function Get-OcrMaxReadableTemperature($Status) {
    $values = @()
    if ($null -ne $Status.CpuTemp) { $values += [double]$Status.CpuTemp }
    if ($null -ne $Status.GpuTemp) { $values += [double]$Status.GpuTemp }
    if ($values.Count -eq 0) { return $null }
    return [double](($values | Sort-Object -Descending | Select-Object -First 1))
}

function Get-OcrPrimaryTemperature($Status) {
    if ($script:OcrThermalPrimaryDevice -eq "GPU") {
        if ($null -ne $Status.GpuTemp) { return [double]$Status.GpuTemp }
        return $null
    }
    if ($null -ne $Status.CpuTemp) { return [double]$Status.CpuTemp }
    return $null
}

function Show-OcrEmergencyTemperatureWarning($Temperature) {
    if ($script:OcrThermalEmergencyPromptShown) { return }
    $script:OcrThermalEmergencyPromptShown = $true
    try {
        $tempText = Format-OcrMetricValue $Temperature "°C"
        [System.Windows.MessageBox]::Show(
            $Window,
            ("检测到设备温度已达到警戒线（{0}）。OCR 将在当前 block 结束后暂停降温。建议终止任务或等待温度下降后继续。" -f $tempText),
            "温度警戒",
            [System.Windows.MessageBoxButton]::OK,
            [System.Windows.MessageBoxImage]::Warning
        ) | Out-Null
    } catch {}
}

function Confirm-OcrStartTemperature {
    $status = Get-OcrResourceStatus
    $primaryTemp = Get-OcrPrimaryTemperature $status
    if ($null -eq $primaryTemp -or [double]$primaryTemp -lt 85.0) { return $true }
    try {
        $deviceText = if ($script:OcrThermalPrimaryDevice -eq "GPU") { "GPU" } else { "CPU" }
        $tempText = Format-OcrMetricValue $primaryTemp "°C"
        $result = [System.Windows.MessageBox]::Show(
            $Window,
            ("当前 {0} 温度已经达到 {1}，不建议立即开始 OCR。是否仍要继续？" -f $deviceText, $tempText),
            "启动前温度提醒",
            [System.Windows.MessageBoxButton]::YesNo,
            [System.Windows.MessageBoxImage]::Warning
        )
        return ($result -eq [System.Windows.MessageBoxResult]::Yes)
    } catch {
        return $true
    }
}

function Update-OcrThermalProtectionState($Status) {
    if (-not $script:OcrControlFile) { return }
    if ($script:StopRequested) { return }

    $thermal = Get-OcrThermalConfig
    $cooldown = [double]$thermal.CooldownSleep
    $pause = $false
    $action = "无"
    $primaryTemp = Get-OcrPrimaryTemperature $Status
    $maxTemp = Get-OcrMaxReadableTemperature $Status
    $showEmergencyTemperature = $null

    if ($null -ne $maxTemp -and [double]$maxTemp -ge 92.0) {
        $pause = $true
        $action = "紧急暂停"
        $script:OcrThermalPauseActive = $true
        $script:OcrThermalResumeStableSince = $null
        $showEmergencyTemperature = $maxTemp
    } elseif ($thermal.Mode -eq "safe" -and $null -ne $primaryTemp) {
        if ([double]$primaryTemp -ge 86.0) {
            $pause = $true
            $action = "暂停降温"
            $script:OcrThermalPauseActive = $true
            $script:OcrThermalResumeStableSince = $null
        } elseif ($script:OcrThermalPauseActive) {
            if ([double]$primaryTemp -le 78.0) {
                if (-not $script:OcrThermalResumeStableSince) {
                    $script:OcrThermalResumeStableSince = Get-Date
                }
                if (((Get-Date) - $script:OcrThermalResumeStableSince).TotalSeconds -ge 5) {
                    $script:OcrThermalPauseActive = $false
                    $script:OcrThermalResumeStableSince = $null
                    $action = "恢复识别"
                } else {
                    $pause = $true
                    $action = "暂停降温"
                }
            } else {
                $pause = $true
                $action = "暂停降温"
                $script:OcrThermalResumeStableSince = $null
            }
        } elseif ([double]$primaryTemp -ge 80.0) {
            $cooldown = [Math]::Max($cooldown, 1.0)
            $action = "降速中"
        }
    } else {
        $script:OcrThermalPauseActive = $false
        $script:OcrThermalResumeStableSince = $null
    }

    $script:OcrThermalProtectionAction = $action
    $script:OcrThermalCurrentCooldownSeconds = $cooldown
    Write-OcrControlFile $script:OcrControlFile $thermal.Mode $cooldown $false $pause
    if ($null -ne $showEmergencyTemperature) {
        Show-OcrEmergencyTemperatureWarning $showEmergencyTemperature
    }
}

function Update-OcrResourceProgressText {
    if (-not $script:OcrProgressThermalText) { return }
    $status = Get-OcrResourceStatus
    Update-OcrThermalProtectionState $status
    $resourceText = $status.Text
    $prefix = [string]$script:OcrResourceStatusPrefix
    $actionText = "保护动作：" + [string]$script:OcrThermalProtectionAction
    if ([string]::IsNullOrWhiteSpace($prefix)) {
        Update-OcrThermalProgressText ($actionText + "`n" + $resourceText)
    } else {
        Update-OcrThermalProgressText ($prefix + "，" + $actionText + "`n" + $resourceText)
    }
}

function New-OcrProgressFilePath {
    return (Join-Path ([IO.Path]::GetTempPath()) ("nikke_ocr_progress_{0}.json" -f ([Guid]::NewGuid().ToString("N"))))
}

function New-OcrControlFilePath {
    return (Join-Path ([IO.Path]::GetTempPath()) ("nikke_ocr_control_{0}.json" -f ([Guid]::NewGuid().ToString("N"))))
}

function Write-OcrControlFile($Path, $Mode, [double]$CooldownSleep, [bool]$Terminate = $false, [bool]$Pause = $false) {
    if (-not $Path) { return }
    try {
        $payload = [ordered]@{
            mode = if ($Mode -eq "performance") { "performance" } else { "safe" }
            action = if ($Terminate) { "terminate" } elseif ($Pause) { "pause" } else { "none" }
            requested_sleep_seconds = [Math]::Max(0.0, [double]$CooldownSleep)
            pause = [bool]$Pause
            terminate = [bool]$Terminate
            updated_at = (Get-Date).ToString("s")
        }
        $json = $payload | ConvertTo-Json -Depth 4
        $encoding = [Text.UTF8Encoding]::new($false)
        [IO.File]::WriteAllText($Path, $json, $encoding)
    } catch {}
}

function Request-OcrRecognitionStop {
    $script:StopRequested = $true
    $script:OcrStopRequestTime = Get-Date
    if ($script:OcrControlFile) {
        $thermal = Get-OcrThermalConfig
        Write-OcrControlFile $script:OcrControlFile $thermal.Mode ([double]$thermal.CooldownSleep) $true $false
    }
    if ($script:OcrProgressStopButton) { $script:OcrProgressStopButton.IsEnabled = $false }
    Update-OcrProgressWindow "正在请求终止 OCR，当前 block 结束后会停止..."
    Append-Log "OCR stop requested by user."
}

function Format-OcrEtaText($Seconds) {
    if ($null -eq $Seconds) { return "计算中" }
    try {
        $secondsValue = [double]$Seconds
    } catch {
        return "计算中"
    }
    if ($secondsValue -lt 0) { return "计算中" }

    $rounded = [int][Math]::Ceiling($secondsValue)
    if ($rounded -lt 60) { return ("约 {0} 秒" -f $rounded) }

    $minutes = [int][Math]::Floor($rounded / 60)
    $secondsPart = $rounded % 60
    if ($minutes -lt 60) { return ("约 {0} 分 {1} 秒" -f $minutes, $secondsPart) }

    $hours = [int][Math]::Floor($minutes / 60)
    $minutesPart = $minutes % 60
    return ("约 {0} 小时 {1} 分" -f $hours, $minutesPart)
}

function Format-OcrElapsedText($Seconds) {
    if ($null -eq $Seconds) { return "计算中" }
    try {
        $secondsValue = [double]$Seconds
    } catch {
        return "计算中"
    }
    if ($secondsValue -lt 0) { return "计算中" }
    $rounded = [int][Math]::Floor($secondsValue)
    if ($rounded -lt 60) { return ("{0} 秒" -f $rounded) }
    $minutes = [int][Math]::Floor($rounded / 60)
    $secondsPart = $rounded % 60
    if ($minutes -lt 60) { return ("{0} 分 {1} 秒" -f $minutes, $secondsPart) }
    $hours = [int][Math]::Floor($minutes / 60)
    $minutesPart = $minutes % 60
    return ("{0} 小时 {1} 分" -f $hours, $minutesPart)
}

function Get-OcrProgressElapsedText {
    if (-not $script:OcrProgressStartedAt) { return "0 秒" }
    return Format-OcrElapsedText (((Get-Date) - $script:OcrProgressStartedAt).TotalSeconds)
}

function Update-OcrElapsedProgressWindow {
    if (-not $script:OcrProgressLastPrefix) { return }
    $text = $script:OcrProgressLastPrefix + "，已用时 " + (Get-OcrProgressElapsedText)
    Update-OcrProgressWindow $text $script:OcrProgressLastPercent
}

function Set-OcrProgressTimedStatus($Prefix, $Percent = $null) {
    $script:OcrProgressLastPrefix = $Prefix
    $script:OcrProgressLastPercent = $Percent
    Update-OcrElapsedProgressWindow
}

function Update-OcrProgressFromFile($ProgressFile, $DefaultLabel, $PercentStart = 0, $PercentSpan = 100) {
    if (-not $ProgressFile -or -not (Test-Path $ProgressFile)) { return $false }
    try {
        $raw = Get-Content -LiteralPath $ProgressFile -Raw -Encoding UTF8
        if ([string]::IsNullOrWhiteSpace($raw)) { return $false }
        $data = $raw | ConvertFrom-Json

        $completed = 0
        $total = 0
        $percent = 0.0
        if ($null -ne $data.completed) { $completed = [int]$data.completed }
        if ($null -ne $data.total) { $total = [int]$data.total }
        if ($null -ne $data.percent) { $percent = [double]$data.percent }

        $label = [string]$data.label
        if ([string]::IsNullOrWhiteSpace($label)) { $label = $DefaultLabel }

        if ($total -gt 0) {
            $completedText = ("{0}/{1}" -f $completed, $total)
        } else {
            $completedText = "准备中"
        }

        $percentText = $percent.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
        $mappedPercent = [double]$PercentStart + ([double]$PercentSpan * $percent / 100.0)
        $prefix = "OCR 识别中：{0}，{1}（{2}%）" -f $label, $completedText, $percentText
        Set-OcrProgressTimedStatus $prefix $mappedPercent
        return $true
    } catch {
        return $false
    }
}

function Complete-OcrProgressWindow($Succeeded) {
    if (-not $script:OcrProgressWindow) { return }
    $completedTitle = "任务完成，指挥官"
    $script:OcrProgressWindow.Title = $completedTitle
    if ($script:OcrProgressTitleText) { $script:OcrProgressTitleText.Text = $completedTitle }
    if ($script:OcrProgressMessageText) { $script:OcrProgressMessageText.Visibility = "Collapsed" }
    if ($script:OcrProgressBar) {
        $script:OcrProgressBar.IsIndeterminate = $false
        $script:OcrProgressBar.Value = 100
    }
    if ($script:OcrProgressDetailText) {
        if ($Succeeded) {
            $script:OcrProgressDetailText.Text = "OCR 导出完成，JSON / Excel 文件已生成。"
        } else {
            $script:OcrProgressDetailText.Text = "OCR 导出结束，但存在警告，请查看运行日志。"
        }
    }
    if ($script:OcrProgressStopButton) { $script:OcrProgressStopButton.Visibility = "Collapsed" }
    if ($script:OcrProgressCloseButton) { $script:OcrProgressCloseButton.Visibility = "Visible" }
    if ($script:OcrProgressOpenLogButton) {
        $script:OcrProgressOpenLogButton.Visibility = if ((-not $Succeeded) -and $script:OcrProgressLogPath -and (Test-Path $script:OcrProgressLogPath)) { "Visible" } else { "Collapsed" }
    }
    if ($script:OcrProgressOpenDataFolderButton) {
        $script:OcrProgressOpenDataFolderButton.Visibility = if ($Succeeded -and $script:OcrProgressOutputFolder -and (Test-Path $script:OcrProgressOutputFolder)) { "Visible" } else { "Collapsed" }
    }
    try { $script:OcrProgressWindow.Topmost = $false } catch {}
    Refresh-Ui
}

function Get-AvailableMemoryGb {
    try {
        $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
        return [Math]::Round(([double]$os.FreePhysicalMemory / 1024 / 1024), 2)
    } catch {
        try {
            $counter = Get-Counter '\Memory\Available MBytes' -ErrorAction Stop
            return [Math]::Round(([double]$counter.CounterSamples[0].CookedValue / 1024), 2)
        } catch {
            return $null
        }
    }
}

function Warn-LowMemoryForSeason {
    # NIKKE_DISABLED_LOW_MEMORY_20260630: Low-memory warning/mode workflow is parked with the original body retained below.
    <#
    $availableGb = Get-AvailableMemoryGb
    if ($null -eq $availableGb) { return }
    if ($availableGb -ge $SeasonMemoryWarnGb) { return }

    $availableText = $availableGb.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
    $memoryLinePrefix = '"\u5f53\u524d\u53ef\u7528\u5185\u5b58\u7ea6 "' | ConvertFrom-Json
    $memoryLineSuffix = '" GB\u3002"' | ConvertFrom-Json
    $message = $TextLowMemoryMessage + "`n`n" + $memoryLinePrefix + $availableText + $memoryLineSuffix
    Append-Log ("Low available memory: " + $availableText + " GB")
    Show-TopMessage $message $TextLowMemoryTitle ([System.Windows.MessageBoxImage]::Warning)
    #>
    return
}

function Test-GameReadyForCapture {
    if ([NativeWin]::IsNikkeRunning()) { return $true }

    Update-Process-Status
    Append-Log $TextGameMissingMessage
    Show-TopMessage $TextGameMissingMessage $TextGameMissingTitle ([System.Windows.MessageBoxImage]::Warning)
    return $false
}

function Stop-ActiveCapture {
    if ($script:ActiveCaptureProcess -and -not $script:ActiveCaptureProcess.HasExited) {
        try {
            $script:StopRequested = $true
            $script:ActiveCaptureProcess.Kill()
            Append-Log "Capture stopped by Alt+2."
            Show-TopMessage $TextStopMessage $TextStopTitle ([System.Windows.MessageBoxImage]::Warning)
        } catch {
            Append-Log ("Stop failed: " + $_.Exception.Message)
        }
    }
}

$script:StopHotkeyWasDown = $false
$script:StopHotkeyTimer = New-Object Windows.Threading.DispatcherTimer
$script:StopHotkeyTimer.Interval = [TimeSpan]::FromMilliseconds(80)
$script:StopHotkeyTimer.Add_Tick({
    $altDown = (([int][NativeWin]::GetAsyncKeyState(0x12) -band 0x8000) -ne 0)
    $twoDown = (([int][NativeWin]::GetAsyncKeyState(0x32) -band 0x8000) -ne 0)
    $hotkeyDown = $altDown -and $twoDown

    if ($hotkeyDown -and -not $script:StopHotkeyWasDown) {
        Stop-ActiveCapture
    }

    $script:StopHotkeyWasDown = $hotkeyDown
})
$script:StopHotkeyTimer.Start()

function Update-OcrSelectedPath {
    if (-not $OcrSelectedPathText) { return }
    if (-not $SelectedOcrImagePath) {
        $OcrSelectedPathText.Text = "-"
    } elseif (Test-Path $SelectedOcrImagePath) {
        $OcrSelectedPathText.Text = $SelectedOcrImagePath
    } else {
        $OcrSelectedPathText.Text = ("未找到文件：" + $SelectedOcrImagePath)
    }
}

function Get-OcrSeasonImageKind($Path) {
    if (-not $Path) { return $null }
    $fileName = [IO.Path]::GetFileNameWithoutExtension($Path).ToLowerInvariant()

    if ($fileName.Contains("top8-决赛") -or $fileName.Contains("to8-决赛")) { return "top8" }
    if ($fileName.Contains("64进32全部")) { return "group64" }
    if ($fileName.Contains("32进16全部")) { return "group32" }
    if ($fileName.Contains("16进8全部")) { return "group16" }

    return $null
}

function Test-OcrSlotDuplicateFileName([string]$SlotKey, [string]$Path) {
    if (-not $Path) { return $false }
    $leafName = [IO.Path]::GetFileName($Path)
    foreach ($key in $script:OcrSeasonImageSlots.Keys) {
        if ($key -eq $SlotKey) { continue }
        $existing = $script:OcrSeasonImageSlots[$key]
        if (-not $existing) { continue }
        if ([string]::Equals([IO.Path]::GetFileName($existing), $leafName, [StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Get-OcrSlotControls($SlotKey) {
    switch ($SlotKey) {
        "top8" { return @{ Image = $OcrSlotTop8Image; Empty = $OcrSlotTop8EmptyImage; Plus = $OcrSlotTop8Plus; Clear = $OcrSlotTop8ClearButton } }
        "group16" { return @{ Image = $OcrSlotGroup16Image; Empty = $OcrSlotGroup16EmptyImage; Plus = $OcrSlotGroup16Plus; Clear = $OcrSlotGroup16ClearButton } }
        "group32" { return @{ Image = $OcrSlotGroup32Image; Empty = $OcrSlotGroup32EmptyImage; Plus = $OcrSlotGroup32Plus; Clear = $OcrSlotGroup32ClearButton } }
        "group64" { return @{ Image = $OcrSlotGroup64Image; Empty = $OcrSlotGroup64EmptyImage; Plus = $OcrSlotGroup64Plus; Clear = $OcrSlotGroup64ClearButton } }
    }
    return @{ Image = $null; Empty = $null; Plus = $null; Clear = $null }
}

function Initialize-OcrSlotEmptyImage($Image) {
    if (-not $Image) { return }
    if ($Image.Source) { return }
    if (Test-Path $OcrSlotEmptyImagePath) {
        $Image.Source = New-Bitmap $OcrSlotEmptyImagePath
    }
}

function Set-OcrSlotVisual($SlotKey, $Path) {
    $controls = Get-OcrSlotControls $SlotKey
    $image = $controls.Image
    $empty = $controls.Empty
    $plus = $controls.Plus
    $clear = $controls.Clear
    Initialize-OcrSlotEmptyImage $empty
    if ($Path -and (Test-Path $Path)) {
        if ($image) {
            $selectedVisualPath = if (Test-Path $OcrSlotSelectedImagePath) { $OcrSlotSelectedImagePath } else { $Path }
            $image.Source = New-Bitmap $selectedVisualPath
            $image.Visibility = "Visible"
        }
        if ($empty) { $empty.Visibility = "Collapsed" }
        if ($plus) { $plus.Visibility = "Collapsed" }
        if ($clear) { $clear.Visibility = "Visible" }
    } else {
        if ($image) {
            $image.Source = $null
            $image.Visibility = "Collapsed"
        }
        if ($empty) { $empty.Visibility = "Visible" }
        if ($plus) { $plus.Visibility = "Visible" }
        if ($clear) { $clear.Visibility = "Collapsed" }
    }
}

function Set-OcrStatusReady($Element, [bool]$Ready) {
    if (-not $Element) { return }
    if ($Ready) {
        $Element.Text = '"\u5df2\u5c31\u7eea"' | ConvertFrom-Json
        $Element.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString("#4EEA9E")
    } else {
        $Element.Text = '"\u672a\u5c31\u7eea"' | ConvertFrom-Json
        $mutedColor = if ($CurrentTheme -eq "pink") { "#9B8090" } else { "#8195AA" }
        $Element.Foreground = [Windows.Media.BrushConverter]::new().ConvertFromString($mutedColor)
    }
}

function Update-OcrSeasonSlotStatuses {
    if (-not $script:OcrSeasonImageSlots) { return }
    foreach ($slotKey in @("top8", "group16", "group32", "group64")) {
        Set-OcrSlotVisual $slotKey $script:OcrSeasonImageSlots[$slotKey]
    }

    $ready = @{
        top8 = $false
        group16 = $false
        group32 = $false
        group64 = $false
    }
    foreach ($path in $script:OcrSeasonImageSlots.Values) {
        $kind = Get-OcrSeasonImageKind $path
        if ($kind -and $ready.ContainsKey($kind)) {
            $ready[$kind] = $true
        }
    }

    Set-OcrStatusReady $OcrStatusTop8 $ready.top8
    Set-OcrStatusReady $OcrStatusGroup16 $ready.group16
    Set-OcrStatusReady $OcrStatusGroup32 $ready.group32
    Set-OcrStatusReady $OcrStatusGroup64 $ready.group64
}

function Select-OcrImage([string]$SlotKey = $null) {
    $dialog = New-Object Microsoft.Win32.OpenFileDialog
    $dialog.Title = "选择赛季全部战斗数据图像"
    $dialog.Filter = "PNG / JPG 图像 (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg"
    $dialog.CheckFileExists = $true
    $dialog.Multiselect = $false
    $dialog.InitialDirectory = Get-OutputDateFolder
    if (-not (Test-Path $dialog.InitialDirectory)) {
        $dialog.InitialDirectory = $OutputRoot
    }
    if ($dialog.ShowDialog($Window)) {
        $extension = [IO.Path]::GetExtension($dialog.FileName).ToLowerInvariant()
        if ($extension -notin @(".png", ".jpg", ".jpeg")) {
            Show-TopMessage "只能选择 PNG 或 JPG 格式的图像文件。" "文件格式不支持" ([System.Windows.MessageBoxImage]::Warning)
            return
        }
        if ($SlotKey -and (Test-OcrSlotDuplicateFileName $SlotKey $dialog.FileName)) {
            Show-TopMessage "4个卡槽不得同时选择同名文件，请指挥官选择另一张图像。" "文件重复" ([System.Windows.MessageBoxImage]::Warning)
            return
        }
        $script:SelectedOcrImagePath = $dialog.FileName
        if ($SlotKey -and $script:OcrSeasonImageSlots.ContainsKey($SlotKey)) {
            $script:OcrSeasonImageSlots[$SlotKey] = $dialog.FileName
        }
        Update-OcrSelectedPath
        Update-OcrSeasonSlotStatuses
    }
}

function Clear-OcrSeasonSlot([string]$SlotKey) {
    if (-not $SlotKey -or -not $script:OcrSeasonImageSlots.ContainsKey($SlotKey)) { return }
    $clearedPath = $script:OcrSeasonImageSlots[$SlotKey]
    $script:OcrSeasonImageSlots[$SlotKey] = $null
    if ($script:SelectedOcrImagePath -eq $clearedPath) {
        $script:SelectedOcrImagePath = $script:OcrSeasonImageSlots.Values |
            Where-Object { $_ -and (Test-Path $_) } |
            Select-Object -First 1
    }
    Update-OcrSelectedPath
    Update-OcrSeasonSlotStatuses
}

function Get-OcrSeasonSelectedImageSpecs {
    $mapping = @(
        @{ Key = "group64"; Argument = "--season-group64-image"; Label = "64进32全部战斗数据（详）" },
        @{ Key = "group32"; Argument = "--season-group32-image"; Label = "32进16全部战斗数据（详）" },
        @{ Key = "group16"; Argument = "--season-group16-image"; Label = "16进8全部战斗数据（详）" },
        @{ Key = "top8"; Argument = "--season-top8-image"; Label = "TOP8-决赛战斗数据（详）" }
    )
    $pathsByKind = @{}
    foreach ($path in (Get-OcrSeasonSelectedImagePaths)) {
        $kind = Get-OcrSeasonImageKind $path
        if (-not $kind) { continue }
        if (-not $pathsByKind.ContainsKey($kind)) {
            $pathsByKind[$kind] = $path
        }
    }

    $items = @()
    foreach ($item in $mapping) {
        if ($pathsByKind.ContainsKey($item.Key)) {
            $items += [PSCustomObject]@{
                Key = $item.Key
                Argument = $item.Argument
                Label = $item.Label
                Path = $pathsByKind[$item.Key]
            }
        }
    }
    return $items
}

function Get-OcrSeasonSelectedImagePaths {
    $paths = @()
    foreach ($slotKey in @("top8", "group16", "group32", "group64")) {
        $path = $script:OcrSeasonImageSlots[$slotKey]
        if ($path) { $paths += $path }
    }
    return $paths
}

function Start-OcrRecognition {
    Set-Running $true
    Set-Log "Preparing OCR recognition..."
    Refresh-Ui
    $completed = $false
    $progressFile = $null
    $controlFile = $null
    $script:StopRequested = $false
    $script:OcrStopRequestTime = $null
    $script:OcrForceStopPromptShown = $false
    $script:OcrControlFile = $null
    $script:OcrThermalProtectionAction = "无"
    $script:OcrThermalPauseActive = $false
    $script:OcrThermalResumeStableSince = $null
    $script:OcrThermalEmergencyPromptShown = $false
    $script:OcrThermalCurrentCooldownSeconds = 0.0
    try {
        if (-not (Test-Path $OcrToolPath)) {
            Append-Log "OCR tool was not found."
            return
        }
        if (-not $OcrPythonExe -and -not $OcrGpuPythonExe) {
            Append-Log "No Python runtime with PaddleOCR was found."
            return
        }
        $seasonImagePaths = @(Get-OcrSeasonSelectedImagePaths)
        $seasonImageSpecs = @(Get-OcrSeasonSelectedImageSpecs)
        $useSeasonMode = ($seasonImagePaths.Count -eq 4)
        $activeSingleImagePath = $SelectedOcrImagePath
        if ($seasonImagePaths.Count -in @(2, 3)) {
            Append-Log "OCR cannot start with only 2 or 3 season images selected."
            Show-TopMessage "卡槽仅选择 2 张或 3 张图时无法执行识别；请选择 1 张进行单图识别，或选择完整 4 张进行汇总识别。" "战斗图像识别" ([System.Windows.MessageBoxImage]::Warning)
            return
        }
        if ($seasonImagePaths.Count -eq 1) {
            $activeSingleImagePath = $seasonImagePaths[0]
            $script:SelectedOcrImagePath = $activeSingleImagePath
        }
        if ($useSeasonMode) {
            $missingSeasonImage = $seasonImageSpecs | Where-Object { -not (Test-Path $_.Path) } | Select-Object -First 1
            if ($missingSeasonImage) {
                Append-Log ("Season OCR image not found: " + $missingSeasonImage.Path)
                Show-TopMessage ("未找到图像文件：" + $missingSeasonImage.Path) "战斗图像识别" ([System.Windows.MessageBoxImage]::Warning)
                return
            }
            if ($seasonImageSpecs.Count -ne 4) {
                Append-Log "Season OCR requires four recognized season image file names."
                Show-TopMessage "四图汇总识别会按文件名自动排序，请确认4个文件名分别包含：64进32全部、32进16全部、16进8全部战斗、TOP8-决赛（或TO8-决赛）。" "战斗图像识别" ([System.Windows.MessageBoxImage]::Warning)
                return
            }
        } elseif (-not $activeSingleImagePath -or -not (Test-Path $activeSingleImagePath)) {
            Append-Log "Please select an existing post-battle data image."
            return
        }
        $performance = Get-OcrPerformanceConfig
        $activeOcrPythonExe = Get-ActiveOcrPythonExe $performance
        if (-not $activeOcrPythonExe) {
            Append-Log "No active Python runtime with PaddleOCR was found."
            return
        }
        $script:ActiveOcrPythonExe = $activeOcrPythonExe
        $script:OcrThermalPrimaryDevice = if ($performance.UseGpu) { "GPU" } else { "CPU" }
        if (-not (Confirm-OcrStartTemperature)) {
            Append-Log "OCR canceled by startup temperature warning."
            return
        }
        $ocrOutputFolder = Get-OutputDateFolder
        $script:OcrProgressOutputFolder = $ocrOutputFolder
        $selectedOcrLeaf = if ($useSeasonMode) { "四卡槽战斗图像" } else { Split-Path -Leaf $activeSingleImagePath }
        $ocrRunLogPath = New-OcrRunLogFilePath
        $manualOcrMessage = '"\u6b63\u5728\u8bc6\u522b\u6218\u6597\u6570\u636e\u56fe\u50cf\uff0c\u8bf7\u6307\u6325\u5b98\u5148\u73a9\u4f1a\u624b\u673a"' | ConvertFrom-Json
        Show-OcrProgressWindow $manualOcrMessage $ocrRunLogPath $true
        Update-OcrProgressWindow ("准备识别：" + $selectedOcrLeaf)
        Append-Log "Running OCR exporter..."

        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $activeOcrPythonExe
        $progressFile = New-OcrProgressFilePath
        $controlFile = New-OcrControlFilePath
        $script:OcrControlFile = $controlFile
        $thermal = Get-OcrThermalConfig
        Write-OcrControlFile $controlFile $thermal.Mode ([double]$thermal.CooldownSleep) $false $false
        if ($script:StopRequested) {
            Write-OcrControlFile $controlFile $thermal.Mode ([double]$thermal.CooldownSleep) $true $false
        }
        $thermalModeText = if ($thermal.Mode -eq "performance") { "性能优先模式" } else { "过热保护模式" }
        $cooldownText = ([double]$thermal.CooldownSleep).ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
        $script:OcrResourceStatusPrefix = "性能与温度保护：{0}，block 间歇 {1}s" -f $thermalModeText, $cooldownText
        Update-OcrResourceProgressText
        $selectedManifestPath = $null
        if ($useSeasonMode) {
            $arguments = "`"$OcrToolPath`" --output-dir `"$ocrOutputFolder`""
            foreach ($spec in $seasonImageSpecs) {
                $arguments += " $($spec.Argument) `"$($spec.Path)`""
                Append-Log ("Season OCR image: " + $spec.Label + " -> " + (Split-Path -Leaf $spec.Path))
            }
            Update-OcrProgressWindow "正在识别四卡槽战斗图像"
        } else {
            $selectedOcrDir = Split-Path -Parent $activeSingleImagePath
            $selectedOcrStem = [IO.Path]::GetFileNameWithoutExtension($activeSingleImagePath)
            $selectedManifestCandidate = Join-Path $selectedOcrDir ("{0}_manifest.json" -f $selectedOcrStem)
            if ((Test-OcrMediumMemoryMode) -and (Test-Path $selectedManifestCandidate)) {
                $selectedManifestPath = $selectedManifestCandidate
                $arguments = "`"$OcrToolPath`" --manifest `"$selectedManifestPath`" --output-dir `"$ocrOutputFolder`""
                Append-Log ("Using OCR manifest: " + (Split-Path -Leaf $selectedManifestPath))
                Update-OcrProgressWindow ("正在读取小块 manifest：" + (Split-Path -Leaf $selectedManifestPath))
            } else {
                if (Test-Path $selectedManifestCandidate) {
                    Append-Log "Medium memory mode is off; using direct large-image OCR."
                }
                $arguments = "`"$OcrToolPath`" --image `"$activeSingleImagePath`" --output-dir `"$ocrOutputFolder`" --stage-code auto --layout auto"
                Update-OcrProgressWindow ("正在分析截图布局：" + $selectedOcrLeaf)
            }
        }
        # NIKKE_DISABLED_OCR_DEBUG_UI_20260701: Debug split-image export button was removed from the OCR page.
        if ($performance.UseGpu) {
            $arguments += " --use-gpu"
        }
        $arguments = Add-OcrRecognitionOptionArguments $arguments
        $arguments += " --progress-file `"$progressFile`""
        $arguments += " --thermal-mode $($thermal.Mode) --control-file `"$controlFile`" --cooldown-sleep $cooldownText"
        Initialize-OcrRunLog $ocrRunLogPath "Manual OCR recognition" $arguments
        $psi.Arguments = $arguments
        $psi.WorkingDirectory = Split-Path -Parent $OcrToolPath
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
        $psi.StandardErrorEncoding = [Text.UTF8Encoding]::new($false)
        Apply-OcrEncodingEnvironment $psi

        $capturedLines = New-Object System.Collections.Generic.List[string]
        $proc = [System.Diagnostics.Process]::Start($psi)
        $stdoutTask = [ref]$proc.StandardOutput.ReadLineAsync()
        $stderrTask = [ref]$proc.StandardError.ReadLineAsync()
        $script:ActiveCaptureProcess = $proc
        $manualTimeoutSeconds = if ($useSeasonMode) { 21600 } else { Get-AutoOcrTimeoutSeconds "auto" $selectedManifestPath }
        $deadline = (Get-Date).AddSeconds($manualTimeoutSeconds)
        $tick = 0
        while (-not $proc.HasExited -and (Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 200
            Drain-OcrProcessOutput $stdoutTask $stderrTask $proc $ocrRunLogPath $capturedLines
            $tick += 1
            if (($tick % 10) -eq 0) {
                $updated = Update-OcrProgressFromFile $progressFile $selectedOcrLeaf 0 100
                if (-not $updated) {
                    Set-OcrProgressTimedStatus ("OCR 引擎运行中：" + $selectedOcrLeaf) $null
                }
            }
            if (($tick % 5) -eq 0) {
                Update-OcrResourceProgressText
            }
            if ($script:StopRequested -and $script:OcrStopRequestTime -and -not $script:OcrForceStopPromptShown) {
                if (((Get-Date) - $script:OcrStopRequestTime).TotalSeconds -ge 15) {
                    $script:OcrForceStopPromptShown = $true
                    $force = [System.Windows.MessageBox]::Show(
                        $Window,
                        "OCR 当前仍未响应。是否强制结束识别子进程？",
                        "强制结束确认",
                        [System.Windows.MessageBoxButton]::YesNo,
                        [System.Windows.MessageBoxImage]::Warning
                    )
                    if ($force -eq [System.Windows.MessageBoxResult]::Yes) {
                        try { $proc.Kill() } catch {}
                        Add-OcrRunLogLine $ocrRunLogPath "[launcher] OCR process killed after stop request."
                    }
                }
            }
            Update-OcrElapsedProgressWindow
            Refresh-Ui
        }
        try { $proc.WaitForExit(1000) | Out-Null } catch {}
        if ($proc.HasExited) {
            Complete-OcrProcessOutput $stdoutTask $stderrTask $proc $ocrRunLogPath $capturedLines
        } else {
            Drain-OcrProcessOutput $stdoutTask $stderrTask $proc $ocrRunLogPath $capturedLines
        }
        Update-OcrProgressFromFile $progressFile $selectedOcrLeaf 0 100 | Out-Null
        if (-not $proc.HasExited) {
            try { $proc.Kill() } catch {}
            Append-Log "OCR recognition timed out."
            Add-OcrRunLogLine $ocrRunLogPath "[launcher] OCR recognition timed out."
            Update-OcrProgressWindow ("OCR 超时：" + $selectedOcrLeaf)
            return
        }

        if ($script:StopRequested) {
            Append-Log "OCR stopped."
            Add-OcrRunLogLine $ocrRunLogPath "[launcher] OCR stopped by user."
            Update-OcrProgressWindow ("OCR 已停止：" + $selectedOcrLeaf)
        } elseif ($proc.ExitCode -eq 0) {
            $lines = @($capturedLines.ToArray() | Where-Object { $_ }) | Select-Object -Last 5
            if ($lines) {
                Append-Log ($lines -join "`n")
            } else {
                Append-Log "OCR export completed."
            }
            Update-OcrProgressWindow ("已导出 JSON / Excel：" + $selectedOcrLeaf)
            $completed = $true
        } else {
            $text = @($capturedLines.ToArray() | Where-Object { $_ }) | Select-Object -Last 8
            Append-Log ("OCR failed:`n" + ($text -join "`n"))
            Add-OcrRunLogLine $ocrRunLogPath ("[launcher] OCR failed with exit code {0}." -f $proc.ExitCode)
            Update-OcrProgressWindow ("OCR 失败：" + $selectedOcrLeaf)
        }
    } catch {
        Append-Log ("OCR failed: " + $_.Exception.Message)
        if ($ocrRunLogPath) { Add-OcrRunLogLine $ocrRunLogPath ("[launcher] OCR exception: " + $_.Exception.Message) }
        Update-OcrProgressWindow ("OCR 异常：" + $_.Exception.Message)
    } finally {
        if ($progressFile -and (Test-Path $progressFile)) {
            try { Remove-Item -LiteralPath $progressFile -Force } catch {}
        }
        if ($controlFile -and (Test-Path $controlFile)) {
            try { Remove-Item -LiteralPath $controlFile -Force } catch {}
        }
        Set-Running $false
        $script:ActiveCaptureProcess = $null
        $script:ActiveOcrPythonExe = $null
        $script:OcrControlFile = $null
        $script:OcrResourceStatusPrefix = ""
        Close-OcrHardwareMonitor
        Complete-OcrProgressWindow $completed
    }
}

function Get-OcrManifestBlockCount($ManifestPath) {
    if (-not $ManifestPath -or -not (Test-Path $ManifestPath)) { return 0 }
    try {
        $manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($manifest.blocks) { return @($manifest.blocks).Count }
    } catch {
        Append-Log ("Could not read OCR manifest block count: " + $_.Exception.Message)
    }
    return 0
}

function Get-AutoOcrTimeoutSeconds($StageCode, $ManifestPath) {
    $blockCount = Get-OcrManifestBlockCount $ManifestPath
    if ($blockCount -gt 0) {
        # Large all-GROUP OCR jobs can legitimately take hours on CPU-only systems.
        return [Math]::Min(21600, [Math]::Max(1800, 900 + ($blockCount * 300)))
    }
    switch ($StageCode) {
        "group64" { return 14400 }
        "group32" { return 7200 }
        "group16" { return 5400 }
        "top8_pyramid" { return 5400 }
        default { return 3600 }
    }
}

# NIKKE_DISABLED_AUTO_OCR_EXPORT_20260630: Retained for future re-enable; no active caller while Test-AutoOcrExportRequested returns $false.
function Invoke-AutoOcrExport($ImagePath, $StageCode, $LayoutCode, $PercentStart = 0, $PercentSpan = 100) {
    if (-not (Test-Path $OcrToolPath)) {
        Append-Log "OCR tool was not found; screenshot was still saved."
        return $false
    }
    if (-not $OcrPythonExe) {
        Append-Log "No Python runtime with PaddleOCR was found; screenshot was still saved."
        return $false
    }
    if (-not $ImagePath -or -not (Test-Path $ImagePath)) {
        Append-Log "Generated image was not found for OCR export."
        return $false
    }

    $ocrDateFolder = Get-OutputDateFolder
    $imageLeaf = Split-Path -Leaf $ImagePath
    Append-Log "Capture completed. Exporting JSON / Excel..."
    Update-OcrProgressWindow ("准备识别：" + $imageLeaf)
    $progressFile = $null

    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $OcrPythonExe
        $progressFile = New-OcrProgressFilePath
        $ocrRunLogPath = New-OcrRunLogFilePath
        $script:OcrProgressLogPath = $ocrRunLogPath
        $performance = Get-OcrPerformanceConfig
        $imageDir = Split-Path -Parent $ImagePath
        $imageStem = [IO.Path]::GetFileNameWithoutExtension($ImagePath)
        $manifestCandidate = Join-Path $imageDir ("{0}_manifest.json" -f $imageStem)
        $activeManifestPath = $null
        if ((Test-OcrMediumMemoryMode) -and (Test-Path $manifestCandidate)) {
            $activeManifestPath = $manifestCandidate
            $inputArguments = "--manifest `"$activeManifestPath`""
            Append-Log ("Using OCR manifest: " + (Split-Path -Leaf $activeManifestPath))
            Update-OcrProgressWindow ("正在读取小块 manifest：" + (Split-Path -Leaf $activeManifestPath))
        } else {
            if (Test-Path $manifestCandidate) {
                Append-Log "Medium memory mode is off; using direct large-image OCR."
            }
            $inputArguments = "--image `"$ImagePath`" --stage-code $StageCode --layout $LayoutCode"
            Update-OcrProgressWindow ("正在分析截图布局：" + $imageLeaf)
        }
        $arguments = "`"$OcrToolPath`" $inputArguments --output-dir `"$ocrDateFolder`""
        if ($performance.UseGpu) {
            $arguments += " --use-gpu"
        }
        $arguments = Add-OcrRecognitionOptionArguments $arguments
        $arguments += " --progress-file `"$progressFile`""
        Initialize-OcrRunLog $ocrRunLogPath "Automatic OCR export" $arguments
        $psi.Arguments = $arguments
        $psi.WorkingDirectory = Split-Path -Parent $OcrToolPath
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
        $psi.StandardErrorEncoding = [Text.UTF8Encoding]::new($false)
        Apply-OcrEncodingEnvironment $psi

        $timeoutSeconds = Get-AutoOcrTimeoutSeconds $StageCode $activeManifestPath
        $manifestBlockCount = Get-OcrManifestBlockCount $activeManifestPath
        if ($manifestBlockCount -gt 0) {
            Append-Log ("OCR timeout budget: {0}s for {1} manifest blocks." -f $timeoutSeconds, $manifestBlockCount)
        } else {
            Append-Log ("OCR timeout budget: {0}s." -f $timeoutSeconds)
        }

        $capturedLines = New-Object System.Collections.Generic.List[string]
        $proc = [System.Diagnostics.Process]::Start($psi)
        $stdoutTask = [ref]$proc.StandardOutput.ReadLineAsync()
        $stderrTask = [ref]$proc.StandardError.ReadLineAsync()
        $script:ActiveCaptureProcess = $proc
        $deadline = (Get-Date).AddSeconds($timeoutSeconds)
        $tick = 0
        while (-not $proc.HasExited -and (Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 200
            Drain-OcrProcessOutput $stdoutTask $stderrTask $proc $ocrRunLogPath $capturedLines
            $tick += 1
            if (($tick % 10) -eq 0) {
                $updated = Update-OcrProgressFromFile $progressFile $imageLeaf $PercentStart $PercentSpan
                if (-not $updated) {
                    Set-OcrProgressTimedStatus ("OCR 引擎运行中：" + $imageLeaf) $null
                }
            }
            Update-OcrElapsedProgressWindow
            Refresh-Ui
        }
        try { $proc.WaitForExit(1000) | Out-Null } catch {}
        if ($proc.HasExited) {
            Complete-OcrProcessOutput $stdoutTask $stderrTask $proc $ocrRunLogPath $capturedLines
        } else {
            Drain-OcrProcessOutput $stdoutTask $stderrTask $proc $ocrRunLogPath $capturedLines
        }
        Update-OcrProgressFromFile $progressFile $imageLeaf $PercentStart $PercentSpan | Out-Null
        if (-not $proc.HasExited) {
            try { $proc.Kill() } catch {}
            Append-Log ("Automatic OCR export timed out after {0}s: {1}" -f $timeoutSeconds, $imageLeaf)
            Add-OcrRunLogLine $ocrRunLogPath ("[launcher] Automatic OCR export timed out after {0}s." -f $timeoutSeconds)
            Update-OcrProgressWindow ("OCR 超时：" + $imageLeaf)
            return $false
        }

        if ($script:StopRequested) {
            Append-Log "Automatic OCR export stopped."
            Add-OcrRunLogLine $ocrRunLogPath "[launcher] Automatic OCR export stopped by user."
            Update-OcrProgressWindow ("OCR 已停止：" + $imageLeaf)
            return $false
        }
        if ($proc.ExitCode -ne 0) {
            $text = @($capturedLines.ToArray() | Where-Object { $_ }) | Select-Object -Last 8
            Append-Log ("Automatic OCR export failed:`n" + ($text -join "`n"))
            Add-OcrRunLogLine $ocrRunLogPath ("[launcher] Automatic OCR export failed with exit code {0}." -f $proc.ExitCode)
            Update-OcrProgressWindow ("OCR 失败：" + $imageLeaf)
            return $false
        }

        $lines = @($capturedLines.ToArray() | Where-Object { $_ }) | Select-Object -Last 4
        Append-Log ("JSON / Excel exported.`n" + ($lines -join "`n"))
        Update-OcrProgressWindow ("已导出 JSON / Excel：" + $imageLeaf)
        return $true
    } catch {
        Append-Log ("Automatic OCR export failed: " + $_.Exception.Message)
        if ($ocrRunLogPath) { Add-OcrRunLogLine $ocrRunLogPath ("[launcher] Automatic OCR export exception: " + $_.Exception.Message) }
        Update-OcrProgressWindow ("OCR 异常：" + $_.Exception.Message)
        return $false
    } finally {
        if ($progressFile -and (Test-Path $progressFile)) {
            try { Remove-Item -LiteralPath $progressFile -Force } catch {}
        }
    }
}

function Start-Capture($GroupSize, $Top8Pyramid = $false) {
    $captureLogPath = New-CaptureDiagnosticsLog $CurrentCaptureMode
    Add-CaptureDiagnosticsLog $captureLogPath ("mode={0}; elevated={1}; script_dir={2}" -f $CurrentCaptureMode, ([Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator), $ScriptDir)
    if (-not (Test-GameReadyForCapture)) {
        Add-CaptureDiagnosticsLog $captureLogPath "NIKKE process was not detected before capture."
        return
    }

    $autoOcrRequested = Test-AutoOcrExportRequested
    if ($autoOcrRequested -and -not [bool]$GroupDetailedDataCheck.IsChecked) {
        Show-TopMessage $TextOcrNeedDetailed $TextSettingHint ([System.Windows.MessageBoxImage]::Information)
        return
    }
    $ocrStageCode = "group64"
    $ocrLayoutCode = "auto"
    if ($CurrentCaptureMode -eq "group") {
        if ([int]$GroupSize -eq 4) { $ocrStageCode = "group32" }
        elseif ([int]$GroupSize -eq 2) { $ocrStageCode = "group16" }
    } elseif ($CurrentCaptureMode -eq "top8") {
        if ($Top8Pyramid) {
            $ocrStageCode = "top8_pyramid"
            $ocrLayoutCode = "top8_pyramid"
        }
        elseif ([int]$GroupSize -eq 8) { $ocrStageCode = "top8" }
        elseif ([int]$GroupSize -eq 4) { $ocrStageCode = "top4" }
        else { $ocrStageCode = "final" }
    } elseif ($CurrentCaptureMode -eq "season") {
        $ocrStageCode = "group64"
        $ocrLayoutCode = "auto"
    }
    if ($CurrentCaptureMode -eq "season") {
        Warn-LowMemoryForSeason
    }
    Set-Running $true
    Set-Log "Preparing capture..."
    Refresh-Ui
    $completed = $false
    $autoOcrCompleted = $true
    $script:StopRequested = $false
    $groupSizeValue = if ($null -ne $GroupSize) { [int]$GroupSize } else { $null }
    $selectedFrame = Get-SelectedFramePath
    $dateFolder = Join-Path $OutputRoot (Get-Date -Format "yyyy-MM-dd")
    New-Item -ItemType Directory -Force -Path $dateFolder | Out-Null
    # The capture loop blocks the WPF dispatcher, so hiding is required instead of a deferred minimize.
    $Window.Hide()
    Refresh-Ui

    try {
        Append-Log "Focusing game window..."
        Add-CaptureDiagnosticsLog $captureLogPath "Focusing NIKKE game window."
        Start-Sleep -Milliseconds 250

        if (-not [NativeWin]::FocusGame()) {
            Append-Log "Game window was not found."
            Add-CaptureDiagnosticsLog $captureLogPath "FocusGame failed: NIKKE process exists but no visible game window was found."
            return
        }

        Start-Sleep -Milliseconds 1000
        if ($CurrentCaptureMode -eq "group") {
            if ($null -eq $groupSizeValue) {
                Append-Log "Group size was not selected."
                return
            }
        } elseif ($CurrentCaptureMode -eq "top8") {
            if (-not $Top8Pyramid -and $groupSizeValue -notin @(2, 4, 8)) {
                Append-Log "TOP8 capture size was not selected."
                return
            }
        }
        $captureTitle = Get-CaptureOutputTitle $groupSizeValue $Top8Pyramid
        $dateLabel = Get-Date -Format "yyyy年M月d日"
        $frameLabel = Get-SelectedFrameLabel
        $fileStem = "{0}{1}" -f $captureTitle, $dateLabel
        if ($frameLabel) { $fileStem = "{0}-{1}" -f $fileStem, $frameLabel }
        $resolutionLabel = Get-CurrentDisplayResolutionLabel
        if ($resolutionLabel) { $fileStem = "{0}-{1}" -f $fileStem, $resolutionLabel }
        $output = Get-UniqueOutputPath $dateFolder ("{0}.png" -f $fileStem)
        Append-Log "Running arena capture..."

        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $delayArg = $CaptureDelaySeconds.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
        $detailDelayArg = $DetailCaptureDelaySeconds.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
        if (Test-Path $RoundWorkerExe) {
            $psi.FileName = $RoundWorkerExe
            $arguments = "--output `"$output`" --click-delay $delayArg --detail-click-delay $detailDelayArg --quiet"
        } else {
            if (-not $PythonExe) {
                Append-Log "No usable Python with Pillow was found."
                return
            }
            $psi.FileName = $PythonExe
            $arguments = "`"$StitcherPath`" --output `"$output`" --click-delay $delayArg --detail-click-delay $detailDelayArg --quiet"
        }
        Append-Log ("Worker: " + $psi.FileName)
        if ($CurrentCaptureMode -eq "group") {
            $arguments += " --group-size $groupSizeValue"
            if ($GroupAllDataCheck.IsChecked -and $groupSizeValue -in @(2, 4, 8)) {
                $arguments += " --all-groups"
            }
            if ($GroupSimpleDataCheck.IsChecked) {
                $arguments += " --group-post-data simple"
            } elseif ($GroupDetailedDataCheck.IsChecked) {
                $arguments += " --group-post-data detailed"
            }
        } elseif ($CurrentCaptureMode -eq "top8") {
            if ($Top8Pyramid) {
                $arguments += " --top8-pyramid"
            } else {
                $arguments += " --top8-size $groupSizeValue"
            }
            if ($GroupSimpleDataCheck.IsChecked) {
                $arguments += " --group-post-data simple"
            } elseif ($GroupDetailedDataCheck.IsChecked) {
                $arguments += " --group-post-data detailed"
            }
        } elseif ($CurrentCaptureMode -eq "season") {
            $arguments += " --season-capture"
            $GroupSimpleDataCheck.IsChecked = $false
            $GroupDetailedDataCheck.IsChecked = $true
            $arguments += " --group-post-data detailed"
        } elseif ($CurrentCaptureMode -eq "support") {
            $arguments += " --support-duo"
            if ($SupportStatusCheck.IsChecked) {
                $arguments += " --include-support-status"
            }
        }
        if ($selectedFrame) {
            $arguments += " --framed-output --framed-background `"$selectedFrame`""
        }
        # NIKKE_DISABLED_LOW_MEMORY_20260630: CLI low-memory flag support is retained but not exposed while the mode is disabled.
        <#
        if ($LowMemoryMode) {
            $arguments += " --low-memory"
        }
        #>
        $psi.Arguments = $arguments
        $psi.WorkingDirectory = $ScriptDir
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.StandardOutputEncoding = [Text.Encoding]::UTF8
        $psi.StandardErrorEncoding = [Text.Encoding]::UTF8
        Add-CaptureDiagnosticsLog $captureLogPath ("worker={0}`r`narguments={1}" -f $psi.FileName, $psi.Arguments)

        $proc = [System.Diagnostics.Process]::Start($psi)
        $script:ActiveCaptureProcess = $proc
        if ($CurrentCaptureMode -eq "top8" -and $Top8Pyramid) {
            $timeoutSeconds = 1800
        } elseif ($CurrentCaptureMode -eq "season") {
            $timeoutSeconds = 7200
        } elseif ($CurrentCaptureMode -eq "group" -and $GroupAllDataCheck.IsChecked) {
            $timeoutSeconds = 3600
        } elseif ($CurrentCaptureMode -eq "group" -or $CurrentCaptureMode -eq "top8") {
            $timeoutSeconds = 600
        } else {
            $timeoutSeconds = 180
        }
        $deadline = (Get-Date).AddSeconds($timeoutSeconds)
        while (-not $proc.HasExited -and (Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 200
            Refresh-Ui
        }
        if (-not $proc.HasExited) {
            try { $proc.Kill() } catch {}
            Append-Log "Capture timed out after $timeoutSeconds seconds."
            return
        }

        $stdout = $proc.StandardOutput.ReadToEnd()
        $stderr = $proc.StandardError.ReadToEnd()
        Add-CaptureDiagnosticsLog $captureLogPath ("worker_exit_code={0}" -f $proc.ExitCode)
        if ($stdout) { Add-CaptureDiagnosticsLog $captureLogPath ("stdout:`r`n" + $stdout.Trim()) }
        if ($stderr) { Add-CaptureDiagnosticsLog $captureLogPath ("stderr:`r`n" + $stderr.Trim()) }

        if ($script:StopRequested) {
            Append-Log "Stopped."
        } elseif ($proc.ExitCode -eq 0) {
            $name = Split-Path -Leaf $output
            if ($CurrentCaptureMode -eq "season") {
                Append-Log "Done: $name`nAlso saved: 32进16全部战斗数据（详）, 16进8全部战斗数据（详）, TOP8-决赛战斗数据（详）"
            } else {
                Append-Log "Done: $name"
            }
            # NIKKE_DISABLED_AUTO_OCR_EXPORT_20260630: Capture-time JSON/Excel export is parked; keep this block for future restoration.
            <#
            if ($autoOcrRequested -and -not $script:StopRequested) {
                Show-OcrProgressWindow $TextAutoOcrStartMessage
                $ocrTargets = @()
                if ($CurrentCaptureMode -eq "season") {
                    $outputDir = Split-Path -Parent $output
                    $outputStem = [IO.Path]::GetFileNameWithoutExtension($output)
                    $outputExt = [IO.Path]::GetExtension($output)
                    $ocrTargets += [pscustomobject]@{ Path = $output; Stage = "group64"; Layout = "auto" }
                    $ocrTargets += [pscustomobject]@{ Path = (Join-Path $outputDir ("{0}_group32_all{1}" -f $outputStem, $outputExt)); Stage = "group32"; Layout = "auto" }
                    $ocrTargets += [pscustomobject]@{ Path = (Join-Path $outputDir ("{0}_group16_all{1}" -f $outputStem, $outputExt)); Stage = "group16"; Layout = "auto" }
                    $ocrTargets += [pscustomobject]@{ Path = (Join-Path $outputDir ("{0}_top8_pyramid{1}" -f $outputStem, $outputExt)); Stage = "top8_pyramid"; Layout = "top8_pyramid" }
                } else {
                    $ocrTargets += [pscustomobject]@{ Path = $output; Stage = $ocrStageCode; Layout = $ocrLayoutCode }
                }
                $ocrTargetCount = [Math]::Max(1, $ocrTargets.Count)
                $targetSpan = 100.0 / [double]$ocrTargetCount
                for ($ocrTargetIndex = 0; $ocrTargetIndex -lt $ocrTargets.Count; $ocrTargetIndex++) {
                    $target = $ocrTargets[$ocrTargetIndex]
                    if ($script:StopRequested) { break }
                    $targetStartPercent = [double]$ocrTargetIndex * $targetSpan
                    $targetLabel = "{0}/{1}" -f ($ocrTargetIndex + 1), $ocrTargetCount
                    if (Test-Path $target.Path) {
                        $targetLeaf = Split-Path -Leaf $target.Path
                        Append-Log ("OCR target: " + $targetLeaf)
                        Update-OcrProgressWindow ("OCR 任务 " + $targetLabel + "：" + $targetLeaf) $targetStartPercent
                        if (-not (Invoke-AutoOcrExport $target.Path $target.Stage $target.Layout $targetStartPercent $targetSpan)) {
                            $autoOcrCompleted = $false
                        } else {
                            $targetDonePercent = [Math]::Floor((($ocrTargetIndex + 1) / $ocrTargetCount) * 100)
                            Update-OcrProgressWindow ("OCR 任务 " + $targetLabel + " 已完成：" + $targetLeaf) $targetDonePercent
                        }
                    } else {
                        $missingLeaf = Split-Path -Leaf $target.Path
                        Append-Log ("OCR target missing: " + $missingLeaf)
                        Update-OcrProgressWindow ("OCR 目标文件缺失：" + $missingLeaf) $targetStartPercent
                        $autoOcrCompleted = $false
                    }
                }
                Complete-OcrProgressWindow $autoOcrCompleted
            }
            #>
            if (-not $script:StopRequested) {
                $completed = $true
            }
        } else {
            $text = (($stdout + "`n" + $stderr) -split "`r?`n" | Where-Object { $_ }) | Select-Object -Last 4
            Append-Log ("Capture failed:`n" + ($text -join "`n"))
        }
    } catch {
        Append-Log ("Failed: " + $_.Exception.Message)
        Add-CaptureDiagnosticsLog $captureLogPath ("launcher_exception: " + $_.Exception.ToString())
    } finally {
        Add-CaptureDiagnosticsLog $captureLogPath ("capture_finished; completed={0}; stopped={1}" -f $completed, $script:StopRequested)
        Set-Running $false
        $script:ActiveCaptureProcess = $null
        $Window.Show()
        $Window.WindowState = "Normal"
        $Window.Activate() | Out-Null
        Update-Process-Status
        if ($completed -and -not $autoOcrRequested) {
            Show-TopMessage $TextDoneMessage $TextDoneTitle ([System.Windows.MessageBoxImage]::Information)
        }
    }
}

$ExecuteButton.Add_Click({ Start-Capture $null })
$Group64Button.Add_Click({ Start-Capture 8 })
$Group32Button.Add_Click({ Start-Capture 4 })
$Group16Button.Add_Click({ Start-Capture 2 })
$Top8Button8.Add_Click({ Start-Capture 8 })
$Top8Button4.Add_Click({ Start-Capture 4 })
$Top8ButtonFinal.Add_Click({ Start-Capture 2 })
$Top8PyramidButton.Add_Click({ Start-Capture $null $true })
$SeasonExecuteButton.Add_Click({ Start-Capture $null })
if ($OcrSelectFileButton) { $OcrSelectFileButton.Add_Click({ Select-OcrImage }) }
if ($OcrSlotTop8Button) { $OcrSlotTop8Button.Add_Click({ Select-OcrImage "top8" }) }
if ($OcrSlotGroup16Button) { $OcrSlotGroup16Button.Add_Click({ Select-OcrImage "group16" }) }
if ($OcrSlotGroup32Button) { $OcrSlotGroup32Button.Add_Click({ Select-OcrImage "group32" }) }
if ($OcrSlotGroup64Button) { $OcrSlotGroup64Button.Add_Click({ Select-OcrImage "group64" }) }
if ($OcrSlotTop8ClearButton) { $OcrSlotTop8ClearButton.Add_Click({ Clear-OcrSeasonSlot "top8" }) }
if ($OcrSlotGroup16ClearButton) { $OcrSlotGroup16ClearButton.Add_Click({ Clear-OcrSeasonSlot "group16" }) }
if ($OcrSlotGroup32ClearButton) { $OcrSlotGroup32ClearButton.Add_Click({ Clear-OcrSeasonSlot "group32" }) }
if ($OcrSlotGroup64ClearButton) { $OcrSlotGroup64ClearButton.Add_Click({ Clear-OcrSeasonSlot "group64" }) }
if ($OcrExampleButton) {
    $OcrExampleButton.Add_Click({
        $script:SelectedOcrImagePath = $OcrExamplePath
        Update-OcrSelectedPath
        Update-OcrSeasonSlotStatuses
        Append-Log "Using example image for OCR."
    })
}
if ($OcrRunButton) { $OcrRunButton.Add_Click({ Start-OcrRecognition }) }
if ($OcrOpenFolderButton) {
    $OcrOpenFolderButton.Add_Click({
        Start-Process -FilePath (Get-OutputDateFolder)
    })
}

if ($Check) {
    Set-SubPageMode "season"
    if ($SeasonExecutePanel.Visibility -ne "Visible" -or
        $FrameOptionsPanel.Visibility -ne "Visible" -or
        $GroupPostDataPanel.Visibility -ne "Visible" -or
        $GroupAllDataCheck.Visibility -ne "Collapsed" -or
        $GroupSimpleDataCheck.Visibility -ne "Collapsed" -or
        [bool]$GroupDetailedDataCheck.IsChecked -ne $true -or
        $GroupDetailedDataCheck.IsEnabled -ne $false) {
        throw "season capture page check failed"
    }
    Write-Output "gui check ok"
    return
}

$Window.Add_Closed({
    if ($script:StopHotkeyTimer) {
        $script:StopHotkeyTimer.Stop()
    }
})

# Capture temporarily hides the main window to keep it off the game screen.
# A modal ShowDialog loop exits when its owner is hidden, so use the application
# message loop instead and keep the process alive until the user actually closes it.
$application = [System.Windows.Application]::Current
if (-not $application) {
    $application = New-Object System.Windows.Application
}
$application.ShutdownMode = [System.Windows.ShutdownMode]::OnMainWindowClose
$application.Run($Window) | Out-Null
