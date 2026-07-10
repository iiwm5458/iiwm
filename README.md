# NIKKE C ARENA Tool

Windows tool for `NIKKE` C ARENA automated screenshots, image stitching, and
battle-image OCR exports. The repository contains both supported products:

- **NIKKE C ARENA Tool (full edition):** automated screenshots, stitching,
  local CPU OCR, optional self-configured NVIDIA GPU OCR, Excel/JSON export,
  and roster maintenance.
- **NIKKE C ARENA Screenshot Tool Lite:** automated screenshots and stitching
  only. Its battle-image recognition page is a visual demo that directs users
  to the full edition.

## Release Files

Installers are published through GitHub Releases, rather than committed to the
Git repository:

- Full edition: `NIKKE_Arena_Tool_Setup_0.1.5.exe`
- Lite edition: `NIKKE_Arena_Capture_Lite_Setup_0.1.0.exe`

## Getting Started

End users should install a Release package. Developers and contributors should
read [PROJECT_DEVELOPER_HANDOFF_20260711.md](PROJECT_DEVELOPER_HANDOFF_20260711.md)
before changing code, rebuilding portable runtimes, or creating a release.

The game should be in fullscreen mode. Screenshot actions send input to the
game window and therefore require launching the tool as administrator.

## Authors

- Product direction and project ownership: **夙辛** (`iiwm5458`)
- Engineering collaboration and packaging support: **Codex (GPT-5)**

Codex is an AI engineering assistant and is credited for its contribution; it
does not claim ownership of the project.

## License and Third-Party Notices

The project's original source code is available under the repository
[LICENSE](LICENSE). `NIKKE` game material, third-party libraries, PaddleOCR
models, icons, and other third-party resources remain subject to their own
licenses and rightsholders' terms.
