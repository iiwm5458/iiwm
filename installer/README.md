# Installer Build

The installer is intentionally built from a prepared release directory rather
than directly from the developer workspace. This keeps screenshots, OCR debug
files, model experiments, cached runtimes, and the developer's GUI settings out
of the user package.

1. Rebuild the portable runtimes and offline PaddleOCR models when dependency
   changes are intentional:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_portable_runtimes.ps1 -ReplaceExisting
```

2. Build and validate the release directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_release_directory.ps1 -Version 0.1.0 -ReplaceExisting
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\verify_release_directory.ps1 -ReleaseRoot .\dist\NIKKE_Arena_Tool_0.1.0
```

3. Compile with Inno Setup 6 after reviewing the release directory:

```powershell
ISCC.exe /DAppVersion=0.1.0 /DReleaseRoot="..\dist\NIKKE_Arena_Tool_0.1.0" .\installer\NIKKE_Arena_Tool.iss
```

Or use the combined build command after Inno Setup is installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_installer.ps1 -Version 0.1.0
```

The installer uses a per-user `%LOCALAPPDATA%` installation path. `runtime_core`
is mandatory; `runtime_cpu` is an optional CPU OCR component. GPU OCR is not
redistributed: users run one of the included GPU setup scripts to create their
own `runtime_gpu` after installation.
