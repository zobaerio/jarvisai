# J.A.R.V.I.S Desktop AI — Windows 11

**Latest source:** `Zobaerio-Jarvis-AI/`  
**Version:** 1.5.2 — Consent-based local content search  
**Repository:** https://github.com/zobaerio/jarvisai

The latest readable source tree is committed under `Zobaerio-Jarvis-AI/`. Download/clone this repository, then open that folder and run `install.bat` followed by `run.bat`. Use Python 3.12.x 64-bit on Windows 11.

## New in v1.2.3
- A **OPEN REAL 3D AVATAR STUDIO** button in the desktop dashboard.
- Three.js procedural 3D character meshes for LUNA, RUBY and MAYA with separate body parts, idle motion, waving, blinking and simulated speaking-mouth movement.
- **IMPORT RIGGED .GLB** lets you load a model from your own computer. The browser parses that model locally and does not upload the GLB file.
- Embedded idle/default and named wave/talk clips can be played if they exist inside the imported model.
- A feature inventory and a Bengali guide for generating, rigging and importing your own 3D character.
- Local task history (last 100 tasks), user-confirmed retry, a persistent FIFO command queue, and cooperative cancellation with a cancel control in the desktop dashboard and approval dialog.
- Approval-gated single-file copy/move/rename within allow-listed user folders, with no-overwrite and symlink/path-traversal protection.
- Approval-gated opening of common document/data/image files through Windows default apps; scripts and executables are blocked.
- Consent-based text search across allow-listed user folders, with bounded file/result limits and a warning that matching snippets may reach the configured AI provider.
- A consistent J.A.R.V.I.S icon/wordmark generated from SVG source, installed as the Windows shortcut/window icon, and responsive desktop layout for smaller resizable windows.
- Approved foreground-app actions: title-only window discovery, user-confirmed text paste, strict allow-listed shortcuts, and deterministic checks for local file/folder existence or visible window titles.

The built-in characters are stylized procedural models—not photorealistic or 1:1 recreations of the reference drawings. The app does not automatically generate a matching 3D model from those pictures or invent absent animation clips. For close likeness, create/license a rigged GLB with the needed motion clips first. Natural walking, hair/cloth physics, expressive facial rigging and phoneme-level lip-sync remain unfinished. Maya's supplied source is only a portrait and cannot define missing full-body geometry. The viewer loads Three.js from a CDN and needs internet access plus WebGL support.

Task history and queued commands are stored in `%APPDATA%\\Zobaerio\\Jarvis\\task_history.json` as local, unencrypted JSON. Avoid entering secrets as commands. Saved queued commands require explicit resumption after an app restart. Cancellation cannot interrupt an in-flight model network read immediately and cannot undo an action already started.

## AI Agent desktop actions

The AI agent can inspect visible window titles (not their contents), paste text into a named Windows app, send one allow-listed editing/navigation shortcut, and check basic outcomes such as file/folder existence or a visible window title. Each paste/shortcut asks for confirmation. This is not semantic verification of document quality or task intent; screenshot vision and arbitrary mouse clicking are not implemented.

## Branding and responsive UI

The official SVG mark and wordmark are in `Zobaerio-Jarvis-AI/assets/branding/`. The installer generates a PNG and multi-size Windows ICO with Pillow, then assigns the ICO to the Desktop shortcut. The app uses the same logo in the header/title bar. The desktop window can shrink to 820×560; the right-side utility rail and decorative top nav collapse at narrower widths. The smartphone/Android installer is intentionally a later phase and is not included yet.

## Guides
- [Bengali installation guide](Zobaerio-Jarvis-AI/README_BN.md)
- [Feature status and roadmap](Zobaerio-Jarvis-AI/FEATURE_STATUS.md)
- [3D character generation and rigging guide (Bangla)](Zobaerio-Jarvis-AI/3D_CHARACTER_PIPELINE_BN.md)

## Install and test
1. Download this repository (or clone it) and open `Zobaerio-Jarvis-AI/`.
2. Install [Python 3.12.10 64-bit](https://www.python.org/downloads/release/python-31210/).
3. Run `install.bat`, then `run.bat`.
4. Click **OPEN REAL 3D AVATAR STUDIO** and then **IMPORT RIGGED .GLB** to load your own model.
5. Review the feature status before assuming every planned feature is implemented.

## Safety and QA
Only allow-listed desktop tools are enabled by default; supported file/folder changes ask for approval. Voice services may transmit audio/text to their providers. Syntax, unit tests and JavaScript module parsing run in GitHub Actions; target-device GPU/WebGL, microphone and speaker tests are still required.
