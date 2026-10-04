param(
    [string]$GuiPath = '',
    [string]$OutputRoot = ''
)
$ErrorActionPreference = 'Stop'
if ([Threading.Thread]::CurrentThread.ApartmentState -ne 'STA') { throw 'Run this WPF test with powershell.exe -STA.' }
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ([string]::IsNullOrWhiteSpace($GuiPath)) { $GuiPath = Join-Path $repoRoot 'nikke_capture_lite_launcher.ps1' }
if ([string]::IsNullOrWhiteSpace($OutputRoot)) { $OutputRoot = Join-Path $repoRoot ('work\lite_localization_' + (Get-Date -Format 'yyyyMMdd_HHmmss')) }
$GuiPath = [IO.Path]::GetFullPath($GuiPath)
$OutputRoot = [IO.Path]::GetFullPath($OutputRoot)
$workspacePrefix = [IO.Path]::GetFullPath((Join-Path $repoRoot 'work')).TrimEnd('\') + '\'
if (-not $OutputRoot.StartsWith($workspacePrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Test artifacts must stay within the workspace work directory.' }
$null = New-Item -ItemType Directory -Path $OutputRoot -Force
Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase
$tokens = $null
$parseErrors = $null
$guiAst = [Management.Automation.Language.Parser]::ParseFile($GuiPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$script:LiteTestCount = 0
function Assert-LiteTest([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
    $script:LiteTestCount++
}

# Evaluate only inert resource declarations and function definitions. GUI startup,
# config loading/saving, native input, ShowDialog and process launch are not run.
foreach ($resourceName in @('LiteTranslations', 'LiteExtraTranslations')) {
    $assignment = @($guiAst.EndBlock.Statements | Where-Object {
        $_ -is [Management.Automation.Language.AssignmentStatementAst] -and $_.Left.Extent.Text -ceq ('$script:' + $resourceName)
    })
    if ($assignment.Count -ne 1) { throw "Expected one resource declaration: $resourceName" }
    Invoke-Expression $assignment[0].Extent.Text
}
foreach ($definition in @($guiAst.EndBlock.Statements | Where-Object { $_ -is [Management.Automation.Language.FunctionDefinitionAst] })) {
    Invoke-Expression $definition.Extent.Text
}
foreach ($required in @('New-ManualPromptAudioSettingsDialog', 'New-ProgramHelpDialog', 'Get-LiteLocalizedText', 'Get-LiteLocalizedFormat', 'Set-LiteLocalizedElementText')) {
    Assert-LiteTest ([bool](Get-Command $required -ErrorAction SilentlyContinue)) "Missing testable production function: $required"
}
foreach ($builderName in @('New-ManualPromptAudioSettingsDialog', 'New-ProgramHelpDialog')) {
    $builderDefinition = @($guiAst.EndBlock.Statements | Where-Object { $_ -is [Management.Automation.Language.FunctionDefinitionAst] -and $_.Name -ceq $builderName })[0]
    Assert-LiteTest (-not ($builderDefinition.Extent.Text -match '\.Show(Dialog)?\s*\(')) "$builderName must construct a window without displaying it."
}
# A broken builder or control handler must fail before saving settings, playing
# sound, launching native programs or opening a message dialog.
function Save-CaptureTimingSettings { throw 'Test blocked an unexpected configuration write.' }
function Append-Log { throw 'Test blocked an unexpected application log write.' }
function Start-Process { throw 'Test blocked an unexpected process launch.' }
function Show-ImageToolMessage { throw 'Test blocked an unexpected message dialog.' }

$languages = @('zh', 'ja', 'en', 'ko')
foreach ($entry in @($script:LiteTranslations.PSObject.Properties)) {
    foreach ($language in $languages) {
        if ($null -eq $entry.Value.PSObject.Properties[$language] -or [string]::IsNullOrWhiteSpace([string]$entry.Value.$language)) {
            throw "Missing primary translation: $($entry.Name) / $language"
        }
    }
}
foreach ($key in @($script:LiteExtraTranslations.Keys)) {
    foreach ($language in $languages) {
        if (-not $script:LiteExtraTranslations[$key].ContainsKey($language) -or [string]::IsNullOrWhiteSpace([string]$script:LiteExtraTranslations[$key][$language])) {
            throw "Missing additional translation: $key / $language"
        }
    }
}
Assert-LiteTest $true 'All primary and additional translations have four nonempty languages.'

function Get-LiteTestLogicalNodes($Root) {
    if ($null -eq $Root) { return }
    Write-Output -NoEnumerate $Root
    foreach ($child in [Windows.LogicalTreeHelper]::GetChildren($Root)) {
        if ($child -is [Windows.DependencyObject]) { Get-LiteTestLogicalNodes $child }
    }
}
function Get-LiteTestVisibleText($Root) {
    $text = @()
    foreach ($node in @(Get-LiteTestLogicalNodes $Root)) {
        if ($node -is [Windows.Controls.TextBlock]) { $text += [string]$node.Text }
        elseif ($node -is [Windows.Controls.ContentControl] -and $node.Content -is [string]) { $text += [string]$node.Content }
    }
    return $text
}
function Find-LiteTestNode($Root, [string]$Name) {
    return @(Get-LiteTestLogicalNodes $Root | Where-Object { $_ -is [Windows.FrameworkElement] -and $_.Name -ceq $Name }) | Select-Object -First 1
}
function Layout-LiteTestWindow($Dialog) {
    $content = $Dialog.Content
    $height = if ($Dialog.SizeToContent -eq [Windows.SizeToContent]::Height) { [double]::PositiveInfinity } else { [double]$Dialog.Height }
    $content.Measure([Windows.Size]::new([double]$Dialog.Width, $height))
    if ([double]::IsPositiveInfinity($height)) { $height = [Math]::Max([double]$Dialog.MinHeight, [Math]::Ceiling($content.DesiredSize.Height)) }
    $content.Arrange([Windows.Rect]::new(0, 0, [double]$Dialog.Width, $height))
    $content.UpdateLayout()
    return [Windows.Size]::new([double]$Dialog.Width, $height)
}
function Save-LiteTestWindowPng($Dialog, [string]$Path) {
    $size = Layout-LiteTestWindow $Dialog
    $bitmap = [Windows.Media.Imaging.RenderTargetBitmap]::new([int][Math]::Ceiling($size.Width), [int][Math]::Ceiling($size.Height), 96, 96, [Windows.Media.PixelFormats]::Pbgra32)
    $bitmap.Render($Dialog.Content)
    $encoder = [Windows.Media.Imaging.PngBitmapEncoder]::new()
    $encoder.Frames.Add([Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
    $stream = [IO.File]::Create($Path)
    try { $encoder.Save($stream) } finally { $stream.Dispose() }
}
function Assert-LiteTestButtonsFit($Dialog, [string]$Context) {
    $content = $Dialog.Content
    foreach ($button in @(Get-LiteTestLogicalNodes $content | Where-Object { $_ -is [Windows.Controls.Button] -and $_.Content -is [string] -and $_.Content -ne '×' })) {
        $probe = [Windows.Controls.TextBlock]::new()
        $probe.Text = [string]$button.Content
        $probe.FontFamily = $button.FontFamily
        $probe.FontSize = $button.FontSize
        $probe.FontWeight = $button.FontWeight
        $probe.Measure([Windows.Size]::new([double]::PositiveInfinity, [double]::PositiveInfinity))
        Assert-LiteTest ($button.MinWidth -ge 76) "${Context}: localized action button needs a minimum width."
        Assert-LiteTest ($button.ActualWidth -ge ($probe.DesiredSize.Width + 12)) "${Context}: localized button text is clipped: $($button.Content)"
        $bounds = $button.TransformToAncestor($content).TransformBounds([Windows.Rect]::new(0, 0, $button.ActualWidth, $button.ActualHeight))
        Assert-LiteTest ($bounds.Left -ge -1 -and $bounds.Right -le ($content.ActualWidth + 1) -and $bounds.Bottom -le ($content.ActualHeight + 1)) "${Context}: action button extends outside the dialog."
    }
}

function Get-LiteTestVisualNodes($Root) {
    if ($null -eq $Root) { return }
    Write-Output -NoEnumerate $Root
    $count = [Windows.Media.VisualTreeHelper]::GetChildrenCount($Root)
    for ($index = 0; $index -lt $count; $index++) {
        Get-LiteTestVisualNodes ([Windows.Media.VisualTreeHelper]::GetChild($Root, $index))
    }
}

# Use the actual production glyph style. Its ContentPresenter creates an inner
# text control, which must be protected together with the language Button root.
$glyphStyleMatch = [regex]::Match([IO.File]::ReadAllText($GuiPath), '(?s)<Style x:Key="LanguageGlyphButton".*?</Style>')
Assert-LiteTest $glyphStyleMatch.Success 'Production language-button style is missing.'
$glyphStyleXaml = $glyphStyleMatch.Value.Replace('<Style ', '<Style xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" ')
$glyphStyle = [Windows.Markup.XamlReader]::Parse($glyphStyleXaml)
$nativeLanguages = [ordered]@{
    zh = @{ Name='LanguageZhButton'; Glyph='中'; Tooltip='简体中文'; Width=26 }
    ja = @{ Name='LanguageJaButton'; Glyph='日'; Tooltip='日本語'; Width=26 }
    en = @{ Name='LanguageEnButton'; Glyph='EN'; Tooltip='English'; Width=28 }
    ko = @{ Name='LanguageKoButton'; Glyph='한'; Tooltip='한국어'; Width=26 }
}
$script:LiteSourceTexts = @{}
$script:CurrentCaptureMode = $null
$languageStripRecords = @()
foreach ($theme in @('dark', 'pink')) {
    $script:CurrentTheme = $theme
    $Window = [Windows.Window]::new()
    $Window.Width = 380
    $Window.Height = 70
    $strip = [Windows.Controls.StackPanel]::new()
    $strip.Orientation = 'Horizontal'
    $strip.Background = New-WpfBrush $(if ($theme -eq 'pink') { '#FFF8FC' } else { '#0B1424' })
    $strip.Margin = [Windows.Thickness]::new(12)
    $Window.Content = $strip
    foreach ($languageKey in $nativeLanguages.Keys) {
        $native = $nativeLanguages[$languageKey]
        $button = [Windows.Controls.Button]::new()
        $button.Name = $native.Name
        $button.Content = $native.Glyph
        $button.ToolTip = $native.Tooltip
        $button.Width = $native.Width
        $button.Height = 26
        $button.Margin = [Windows.Thickness]::new(0, 0, 12, 0)
        $button.Style = $glyphStyle
        $button.FontFamily = 'Microsoft YaHei UI'
        $button.FontSize = 13
        $null = $strip.Children.Add($button)
        Set-Variable -Scope Script -Name $native.Name -Value $button
        $null = $button.ApplyTemplate()
    }
    $mediumRadio = [Windows.Controls.RadioButton]::new()
    $mediumRadio.Name = 'ResultSizeMediumTest'
    $mediumRadio.Content = '中'
    $mediumRadio.Height = 26
    $mediumRadio.MinWidth = 120
    $mediumRadio.Foreground = New-WpfBrush $(if ($theme -eq 'pink') { '#805065' } else { '#D7E8F6' })
    $null = $strip.Children.Add($mediumRadio)
    $null = $mediumRadio.ApplyTemplate()
    $null = Layout-LiteTestWindow $Window
    foreach ($language in @('zh', 'ja', 'en', 'ko', 'zh')) {
        # Exercise the real language switch, including both tree traversals and
        # the native glyph update; never just compare Button.Content alone.
        Set-LiteLanguageUi $language
        # An offscreen Window has no HWND-backed visual root. Traverse its laid
        # out content directly, using the same production tree functions.
        Set-LiteLocalizedLogicalTree $strip
        Set-LiteLocalizedVisualTree $strip
        Update-LiteLanguageButtons
        $null = Layout-LiteTestWindow $Window
        Save-LiteTestWindowPng $Window (Join-Path $OutputRoot ($theme + '_' + $language + '_language_buttons.png'))
        foreach ($languageKey in $nativeLanguages.Keys) {
            $native = $nativeLanguages[$languageKey]
            $button = Get-Variable -Scope Script -Name $native.Name -ValueOnly
            $presenters = @(Get-LiteTestVisualNodes $button | Where-Object { $_ -is [Windows.Controls.ContentPresenter] })
            $displayedGlyphs = @(Get-LiteTestVisualNodes $button | Where-Object { $_ -is [Windows.Controls.TextBlock] } | ForEach-Object { [string]$_.Text })
            $languageStripRecords += [PSCustomObject]@{ Theme=$theme; Language=$language; Button=$native.Name; Content=[string]$button.Content; Displayed=$displayedGlyphs }
            $languageStripRecords | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputRoot 'language_button_text.json') -Encoding UTF8
            Assert-LiteTest ($presenters.Count -gt 0 -and $displayedGlyphs.Count -gt 0) "$theme/${language}: language Button did not instantiate its real WPF text template."
            Assert-LiteTest ($displayedGlyphs -ccontains $native.Glyph -and -not ($displayedGlyphs -ccontains 'Medium') -and -not ($displayedGlyphs -ccontains '중간')) "$theme/${language}: $($native.Name) rendered a translated size label: $($displayedGlyphs -join ', ')"
            Assert-LiteTest ([string]$button.ToolTip -ceq $native.Tooltip) "$theme/${language}: language Button changed its native language name."
        }
        $radioTexts = @(Get-LiteTestVisualNodes $mediumRadio | Where-Object { $_ -is [Windows.Controls.TextBlock] } | ForEach-Object { [string]$_.Text })
        Assert-LiteTest ($radioTexts -ccontains (Get-LiteLocalizedText '中')) "$theme/${language}: protecting language glyphs disabled the ordinary medium-size label translation."
    }
    $Window.Close()
}
$Window = $null

$script:ManualClickPromptVolume = 25
$script:ManualClickPromptTimbre = 'musicbox_chime'
$Window = $null
$allOutput = @()
$renderedPairs = @{}
foreach ($theme in @('dark', 'pink')) {
    $script:CurrentTheme = $theme
    $chineseDialogText = @()
    foreach ($language in @('zh', 'ja', 'en', 'ko', 'zh')) {
        $script:LiteLanguage = $language
        $audio = New-ManualPromptAudioSettingsDialog
        $help = New-ProgramHelpDialog
        Assert-LiteTest ($audio -is [Windows.Window] -and -not $audio.IsVisible) "$theme/${language}: audio builder opened a window."
        Assert-LiteTest ($help -is [Windows.Window] -and -not $help.IsVisible) "$theme/${language}: help builder opened a window."
        Assert-LiteTest ($audio.Title -ceq (Get-LiteLocalizedText '音量设置')) "$theme/${language}: audio window title is not localized."
        Assert-LiteTest ($help.Title -ceq (Get-LiteLocalizedText '帮助')) "$theme/${language}: help window title is not localized."
        $audioText = @(Get-LiteTestVisibleText $audio.Content)
        $helpText = @(Get-LiteTestVisibleText $help.Content)
        if ($language -eq 'zh') { $chineseDialogText = @($audioText + $helpText | Where-Object { $_.Length -gt 3 -and $_ -match '[\u4e00-\u9fff]' }) }
        if ($language -ne 'zh') {
            $unchangedChinese = @($audioText + $helpText | Where-Object { $chineseDialogText -ccontains $_ })
            Assert-LiteTest ($unchangedChinese.Count -eq 0) "$theme/${language}: dialog reused a Chinese paragraph or label: $($unchangedChinese -join '; ')"
        }
        foreach ($source in @('音量设置', '仅用于国际服与港澳台服的手动左键确认提示音。', '提示音音量', '提示音音色', '八音盒', '试听', '保存并关闭')) {
            Assert-LiteTest ($audioText -ccontains (Get-LiteLocalizedText $source)) "$theme/${language}: missing translated audio label: $source"
        }
        foreach ($source in @('NIKKE C ARENA Tool 轻量版帮助', '功能简介', '运行方式', '开发初心', '使用与风险提示', '禁止用途', '我已了解')) {
            Assert-LiteTest ($helpText -ccontains (Get-LiteLocalizedText $source)) "$theme/${language}: missing translated help text: $source"
        }
        if ($language -in @('en', 'ko')) {
            Assert-LiteTest (-not (($audioText + $helpText + @($audio.Title, $help.Title)) -join "`n" -match '[\u4e00-\u9fff]')) "$theme/${language}: dialog contains untranslated Chinese."
        }
        $hint = Find-LiteTestNode $audio.Content 'AudioDialogHint'
        Assert-LiteTest ($null -ne $hint -and $hint.TextWrapping -eq [Windows.TextWrapping]::Wrap) "$theme/${language}: audio hint is not wrapped."
        $slider = Find-LiteTestNode $audio.Content 'ManualPromptVolumeSlider'
        $musicbox = Find-LiteTestNode $audio.Content 'ManualPromptMusicboxRadio'
        Assert-LiteTest ($null -ne $slider -and $slider.Minimum -eq 0 -and $slider.Maximum -eq 100 -and $slider.Value -eq 25) "$theme/${language}: audio controls changed volume settings."
        Assert-LiteTest ($null -ne $musicbox -and $musicbox.IsChecked -eq $true) "$theme/${language}: stored musicbox_chime did not select its translated radio."
        $slider.Value = 75
        Assert-LiteTest (@(Get-LiteTestVisibleText $audio.Content) -contains '75%') "$theme/${language}: slider handler lost its local state after builder returned."
        $null = Layout-LiteTestWindow $audio
        $null = Layout-LiteTestWindow $help
        $percentageText = $slider.Tag
        Assert-LiteTest ($percentageText -is [Windows.Controls.TextBlock]) "$theme/${language}: percentage label is not attached to the slider handler."
        $percentageBounds = $percentageText.TransformToAncestor($audio.Content).TransformBounds([Windows.Rect]::new(0, 0, $percentageText.ActualWidth, $percentageText.ActualHeight))
        Assert-LiteTest ($percentageBounds.Right -ge ($audio.Width - 40)) "$theme/${language}: percentage text touches the volume label instead of aligning to the right."
        $helpBodies = @(Get-LiteTestLogicalNodes $help.Content | Where-Object { $_ -is [Windows.Controls.TextBlock] -and $_.Tag -ceq 'LiteHelpBody' })
        Assert-LiteTest ($helpBodies.Count -eq 5 -and @($helpBodies | Where-Object { $_.TextWrapping -ne [Windows.TextWrapping]::Wrap }).Count -eq 0) "$theme/${language}: help paragraphs are not all wrapped."
        $expectedBackground = if ($theme -eq 'pink') { '#F7FFF8FC' } else { '#F40B1424' }
        Assert-LiteTest ($audio.Content.Background.Color.ToString() -ceq $expectedBackground -and $help.Content.Background.Color.ToString() -ceq $expectedBackground) "$theme/${language}: dialogs did not use the selected theme."
        Assert-LiteTest ($hint.ActualWidth -gt 0 -and $hint.ActualWidth -le $audio.Width) "$theme/${language}: audio hint has no usable layout."
        Assert-LiteTestButtonsFit $audio "$theme/$language audio"
        Assert-LiteTestButtonsFit $help "$theme/$language help"
        if (-not $renderedPairs.ContainsKey($theme + '/' + $language)) {
            $renderedPairs[$theme + '/' + $language] = $true
            Save-LiteTestWindowPng $audio (Join-Path $OutputRoot ($theme + '_' + $language + '_audio.png'))
            Save-LiteTestWindowPng $help (Join-Path $OutputRoot ($theme + '_' + $language + '_help.png'))
        }
        $allOutput += [PSCustomObject]@{ Theme=$theme; Language=$language; AudioTitle=$audio.Title; HelpTitle=$help.Title; AudioText=$audioText; HelpText=$helpText; AudioHeight=$audio.Content.ActualHeight }
        $audio.Close()
        $help.Close()
    }
}

$tooltipSource = '检测基础信息页，最长等待 10 秒；超时后仍会截取当前画面。'
$script:LiteLocalizedPropertySources = @{}
$tooltipControl = [Windows.Controls.CheckBox]::new()
$tooltipControl.ToolTip = $tooltipSource
foreach ($language in @('zh', 'ja', 'en', 'ko', 'zh', 'en')) {
    $script:LiteLanguage = $language
    Set-LiteLocalizedElementText $tooltipControl
    Assert-LiteTest ([string]$tooltipControl.ToolTip -ceq (Get-LiteLocalizedText $tooltipSource)) "${language}: string ToolTip lost its original source after language switching."
}
foreach ($language in $languages) {
    $script:LiteLanguage = $language
    $formatted = Get-LiteLocalizedFormat '提示音试听失败：{0}' @('TEST_ERROR_17')
    Assert-LiteTest ($formatted.Contains('TEST_ERROR_17') -and -not $formatted.Contains('{0}')) "${language}: error template dropped its parameter."
    if ($language -ne 'zh') { Assert-LiteTest (-not $formatted.StartsWith('提示音试听失败：')) "${language}: dynamic error message fell back to Chinese." }
}
$audioDefinition = @($guiAst.EndBlock.Statements | Where-Object { $_ -is [Management.Automation.Language.FunctionDefinitionAst] -and $_.Name -eq 'New-ManualPromptAudioSettingsDialog' })[0].Extent.Text
Assert-LiteTest ($audioDefinition.Contains('"musicbox_chime"') -and $audioDefinition.Contains('"8bit"')) 'Localized timbre UI changed the stored transport codes.'
$allOutput | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $OutputRoot 'rendered_text.json') -Encoding UTF8
Write-Output ("Lite localization checks passed: {0}; screenshots and actual dialog texts: {1}" -f $script:LiteTestCount, $OutputRoot)
