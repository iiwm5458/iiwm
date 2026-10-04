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

Every normal launch of either installer uses its fixed default directory:

- Full edition: `C:\NIKKE_C_ARENA_Tool\NIKKE C ARENA Tool`.
- Lite edition: `C:\NIKKE_C_ARENA_Tool\NIKKE C ARENA 截图工具 轻量版`.

Both installers keep their existing, separate AppIds and per-user installation
mode (`PrivilegesRequired=lowest`). `UsePreviousAppDir=no` prevents old
installation records from replacing these defaults, even when an old
installation folder was manually deleted and its uninstall record remains.
`DisableDirPage=no` always lets users inspect and change the directory. Users
who want an in-place upgrade must select their existing directory; existing
settings, screenshots, MODs, and GPU runtimes remain there. Selecting a
different directory creates a separate copy: those files are not automatically
moved from the old directory, and the old installation is not deleted.

The directory page and the final pre-install check reject a directory occupied
by the other edition. The pre-install check verifies that the nearest existing
parent can create and write a temporary subdirectory, then creates and verifies
the selected directory before copying program files. Only its own temporary
probe file and empty probe directory are removed. This also applies to silent
installation. The directory page does not create the target. An unwritable
directory produces a specific error and must be replaced with a writable
location; the installer does not request elevation or change permissions.

`runtime_core` is mandatory; `runtime_cpu` is an optional CPU OCR component.
GPU OCR is not redistributed: users run one of the included GPU setup scripts
to create their own `runtime_gpu` after installation. Neither installer deletes
unlisted files during an in-place upgrade; existing `mods` and `runtime_gpu`
directories remain outside the official installer payload.

For 0.1.23 and later, the full release directory and installer include only
`nikke_input_plugins.py`, the restricted input host. The optional Logitech click
MOD is maintained and distributed separately from this source repository and
installed under the selected full-edition directory's `mods/` folder. Do not add `mods/`, the
standalone Logitech test project, or a driver binary to
the official `[Files]` list, release-directory copy list, or update-patch
payload. The lite installer does not include the host.

After building both installers, build the cross-history patches with
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build_update_patches.ps1 -FullVersion 0.1.25 -LiteVersion 0.1.15`.
The build script refuses to overwrite an existing patch. Run
`tools/test_full_history_update.ps1 -PatchRoot <generated-patch-directory>`
before distribution, and run `tools/test_lite_history_update.ps1` for the Lite
patch. Versioned `RELEASE_NOTES_<FullVersion>.md` and
`RELEASE_NOTES_LITE_<LiteVersion>.md` supply the per-edition update reasons.
The patch fills the plain Python setup base only when
its directory is missing, preserves installed runtimes, and refreshes program,
template, and offline model resources. Host regression tests work without the
private MOD; maintainers additionally validate the approved private package
locally when it is available.
