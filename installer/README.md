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

For 0.1.23 and later, the full release directory and installer include only
`nikke_input_plugins.py`, the restricted input host. The optional Logitech click
MOD is maintained and distributed separately from this source repository and
installed under the user's application data directory. Do not add `mods/`, the
standalone Logitech test project, or a driver binary to
the official `[Files]` list, release-directory copy list, or update-patch
payload. The lite installer does not include the host.

Build the full-only cross-history patch with
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build_update_patches.ps1 -FullVersion 0.1.24 -FullOnly`.
The build script refuses to overwrite an existing patch. Run
`tools/test_full_history_update.ps1 -PatchRoot <generated-patch-directory>`
before distribution. The patch fills the plain Python setup base only when
its directory is missing, preserves installed runtimes, and refreshes program,
template, and offline model resources. Host regression tests work without the
private MOD; maintainers additionally validate the approved private package
locally when it is available.
