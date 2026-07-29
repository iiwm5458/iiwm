# NIKKE C ARENA Tool Project Handoff

Updated: 2026-07-29 (UTC+8)

## Products

This repository produces two Windows products. They must be installed and
updated separately.

| Product | Current source release | Entry point | Scope |
| --- | --- | --- | --- |
| Full edition | `0.1.16` | `run_gui.bat` | Automated screenshots, stitching, image tools, local CPU OCR, optional user-configured GPU OCR, Excel/JSON export, roster maintenance. |
| Capture Lite | `0.1.8` | `run_capture_lite.bat` | Automated screenshots, stitching, image tools, result-page checks, and parameter persistence. The recognition page is a demo that directs users to the full edition. |

The full edition ships an internal Python runtime, CPU PaddleOCR runtime, and
offline OCR models. It does **not** ship CUDA, cuDNN, NVIDIA drivers, or a GPU
Paddle runtime. GPU setup is explicitly user initiated through the included
guides and setup scripts. The lite edition must not contain PaddleOCR, OCR
models, CPU/GPU runtimes, or GPU setup documents.

## Primary Source Files

| Area | Files |
| --- | --- |
| Full GUI | `nikke_gui_launcher.ps1` |
| Lite GUI | `nikke_capture_lite_launcher.ps1` |
| Screenshot automation and stitching | `nikke_round_stitcher.py`, `nikke_round_config.json` |
| Image compression, stitching, and result annotation | `nikke_image_tools.py` |
| OCR CLI and parsing | `dataanalysis/arena_ocr_tool/main.py`, `recognizer/` |
| Roster and result templates | `dataanalysis/arena_ocr_tool/data/nikke_names.json`, `data/defeat_templates/` |
| OCR nickname model | `dataanalysis/arena_ocr_tool/models/nickname/chinese_cht/` |
| Installer definitions | `installer/NIKKE_Arena_Tool.iss`, `installer/NIKKE_Arena_Capture_Lite.iss` |
| Release and patch scripts | `tools/build_*release*.ps1`, `tools/build_*installer*.ps1`, `tools/build_update_patches.ps1` |

Both GUI launchers include a compact Help entry outside the main panel. The
Help dialog describes the product's screenshot and OCR scope, privacy and
legal limits, and the fact that the program does not read, write, scan, inject
into, hook, or otherwise modify game process memory.

## Current Capability Notes

- Three server modes are supported: China, Hong Kong/Macau/Taiwan, and
  international. Automatic process detection is available, with a manual
  override in the GUI. The selected mode determines screenshot behavior and
  filename suffixes.
- Overseas clients use mouse clicks to close pages and return from the group
  stage, avoiding unreliable `Esc` input on those clients. China-server logic
  remains independent.
- Detailed-result capture waits through visible-pixel polling before taking a
  screenshot. Player basic-information capture can optionally use a separate
  polling check. Both are configured in the parameter page.
- Windowed mode supports the intentionally limited single-player, support, and
  champion/runner-up capture workflows. Other automation workflows require
  fullscreen mode.
- The image tool supports up to four selected images at once, JPEG compression,
  vertical/horizontal stitching, and result annotations. The full edition also
  supports battle-image OCR and Excel/JSON exports.

## Release Workflow

Run commands from the repository root in PowerShell. Inno Setup 6 must be
installed.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_installer.ps1 -Version 0.1.16
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_capture_lite_installer.ps1 -Version 0.1.8
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_update_patches.ps1 -FullVersion 0.1.16 -LiteVersion 0.1.8
```

Validate release directories before distributing them:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\verify_release_directory.ps1 -ReleaseRoot .\dist\r_0.1.16
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\verify_capture_lite_release.ps1 -ReleaseRoot .\dist\lite_r_0.1.8
```

The direct-update ZIPs include `apply_update.bat`, `apply_update.ps1`, a
`payload` directory, user instructions, a timestamped changelog, and
`SHA256SUMS.txt`. The updater backs up replaced files to `update_backups` in
the installed application directory.

## Repository Boundaries

Never add the following to Git:

- `runtime_core/`, `runtime_cpu/`, `runtime_gpu/`, `runtime_python310_base/`,
  `wheelhouse_gpu/`, or other bundled Python/GPU runtimes.
- `dist/`, installer EXEs, patch ZIPs, user screenshots, OCR exports, logs,
  local backups, temporary benchmarks, and diagnostic captures.
- NVIDIA/CUDA/cuDNN components or redistributable GPU dependencies.
- Removed historical wallpaper and site-icon assets. Their deletions are
  intentional and must not be reverted merely to make Git status cleaner.

### GPU redistribution rule

Do not package NVIDIA CUDA, cuDNN, Paddle GPU runtimes, or other NVIDIA
redistributables into installers, patches, or GitHub Release assets. These
third-party components have their own current license and redistribution terms;
including them would require a separate legal review, substantially enlarge the
release, and still cannot guarantee compatibility with each user's drivers and
Windows environment. Keep only version-pinned user setup scripts and guides in
the project. Users must obtain and configure their own GPU environment.

The source repository contains the lightweight OCR templates and nickname
model files that the full offline release needs. Keep their license/readme
information alongside them.

## Git Notes

The remote repository is private. Before pushing, check `git status --short`,
stage only source and required assets, and review `git diff --cached --stat`.
Do not force-push or restore intentionally deleted assets. A valid GitHub SSH
deploy key or other authenticated Git transport is required for upload.

## Authors

Original author and product owner: **iiwm (雪瑶 / 夙辛)**.

Engineering collaboration and packaging support: **Codex (GPT-5)**.
