# J.A.R.V.I.S Desktop AI — Windows 11

**Latest source:** `Zobaerio-Jarvis-AI/`  
**Version:** 1.7.3 — bounded voice timeouts  
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
- Consent-gated reading of selected text files with path/size disclosure, provider-transmission notice, symlink/binary blocking and recheck for file changes.
- Task history updates use path-level thread locks, unique fsynced temporary files, atomic replacement and a `.bak` recovery file.
- Settings includes a non-generative `/models` connection check; malformed URLs are rejected and stored API keys are never sent over remote plain HTTP.
- Settings are atomically saved with a local recovery backup and fall back to that backup when the primary JSON becomes unreadable.
- Files can be sent to the Windows Recycle Bin only after approval; this is not a permanent-delete capability.
- AI provider error bodies and raw exception messages are hidden; malformed provider responses return safe diagnostics.
- On startup, stale running tasks are marked failed rather than silently remaining active or being automatically replayed; queued tasks stay queued.
- Create bounded ZIP archives from selected files with explicit approval, source-change checks, no-overwrite publication and source files left unchanged.
- Find duplicate files read-only by local SHA-256 hashes within bounded, user-approved folders; never delete or alter files.
- Consent-based text search across allow-listed user folders, with bounded file/result limits and a warning that matching snippets may reach the configured AI provider.
- A consistent J.A.R.V.I.S icon/wordmark generated from SVG source, installed as the Windows shortcut/window icon, and responsive desktop layout for smaller resizable windows.
- Approved foreground-app actions: title-only window discovery, user-confirmed text paste, strict allow-listed shortcuts, and deterministic checks for local file/folder existence or visible window titles.

The built-in characters are stylized procedural models—not photorealistic or 1:1 recreations of the reference drawings. The app does not automatically generate a matching 3D model from those pictures or invent absent animation clips. For close likeness, create/license a rigged GLB with the needed motion clips first. Natural walking, hair/cloth physics, expressive facial rigging and phoneme-level lip-sync remain unfinished. Maya's supplied source is only a portrait and cannot define missing full-body geometry. The viewer loads Three.js from a CDN and needs internet access plus WebGL support.

Task history and queued commands are stored in `%APPDATA%\\Zobaerio\\Jarvis\\task_history.json` as local, unencrypted JSON. Avoid entering secrets as commands. Saved queued commands require explicit resumption after an app restart. Cancellation cannot interrupt an in-flight model network read immediately and cannot undo an action already started.

## AI Agent desktop actions

Task History distinguishes `COMPLETED`, `PARTIAL`, `FAILED` and `CANCELLED`. Known provider/configuration failures and malformed responses are marked failed; tool exceptions or the agent action budget are marked partial. A selected command that is still `QUEUED` can be cancelled from Task History before execution; tasks that have started cannot be cancelled using that queue control. Task History also supports local search across command/result/progress/tool metadata and filtering by outcome status. This is execution-status reporting, not proof that the user's semantic goal or document quality was achieved.

The AI agent can inspect visible window titles (not their contents), paste text into a named Windows app, send one allow-listed editing/navigation shortcut, and check basic outcomes such as file/folder existence or a visible window title. Each paste/shortcut asks for confirmation. This is not semantic verification of document quality or task intent; screenshot vision and arbitrary mouse clicking are not implemented.

## Branding and responsive UI

The official SVG mark and wordmark are in `Zobaerio-Jarvis-AI/assets/branding/`. The installer generates a PNG and multi-size Windows ICO with Pillow, then assigns the ICO to the Desktop shortcut. The app uses the same logo in the header/title bar. The desktop window can shrink to 820×560; the right-side utility rail and decorative top nav collapse at narrower widths. The Flutter mobile client is available as an Android debug build through GitHub Actions; it is not yet a signed production release and does not provide full Windows desktop-agent parity.

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


## Privacy-safe diagnostics export

Task History can export a support report after explicit confirmation. It contains aggregate task/outcome/action counts, UTC date and duration summaries, app version, OS family and Python version. It excludes task IDs, prompts/commands, result text, file paths and names, progress text, tool names/arguments/outputs and exception details. The export is a JSON file you choose locally; review it before sharing.


## Safe exception reporting

Unexpected tool/worker errors show a bounded exception type and next-step guidance, not raw exception strings that might include local paths, account identifiers, or other sensitive data. Tool-result text is no longer copied into Task History progress events. The full underlying exception detail is intentionally withheld from the user/provider response path.


## Windows portable build

A reproducible PyInstaller one-folder build is defined in `Zobaerio-Jarvis-AI/JARVIS.spec` and `build_portable.bat`. On Windows with Python 3.12 x64, run `install.bat` only if you want the source-based setup; to create a portable package, open `Zobaerio-Jarvis-AI` and run `build_portable.bat`. The output is `dist/JARVIS-Windows-Portable.zip`. GitHub Actions also builds this ZIP on Windows and uploads it as a 14-day workflow artifact. This is an **unsigned** portable build, not a signed installer/MSIX. Online AI endpoints, speech services, and the 3D viewer's Three.js CDN still require their respective connectivity; this does not make the app fully offline.


## Voice reliability

Voice recognition now has a bounded provider-operation timeout, and Edge TTS synthesis/playback is time-limited so a stalled speech service cannot keep the voice worker waiting indefinitely. The local fallback remains best-effort. Microphone, speaker, network, and Windows hardware testing is still required.

## Local system health check

The **RUN SYSTEM HEALTH CHECK** control runs fast local preflight checks for the Python runtime, Windows platform, bundled 3D/branding assets, runtime dependencies, endpoint/model configuration, and—only for cloud endpoints—whether an API key is available in secure storage. It does not send a request to the model endpoint, record microphone audio, inspect user files, or reveal endpoint/API-key values. Local Ollama endpoints do not require a key. Use Settings' separate connection test to check provider reachability.


## v1.7.2 reliability fix

The cloud API-key health check now calls the secure keyring getter with its correct zero-argument signature. A regression test confirms that key availability is reported without displaying the secret value.


## API key quick setup

In Settings, **AUTO SETUP FROM API KEY** recognizes supported OpenRouter, OpenAI, Groq, and Google Gemini API key formats, requests the identified provider's HTTPS model catalog, and selects a recognizable chat model. The key is stored using the existing Windows credential-store integration, not in the settings JSON. Unknown or ambiguous key formats are not sent to guessed providers; configure the provider's OpenAI-compatible base URL and model in Advanced Settings instead. This is not universal native-provider support: an API key alone cannot establish compatibility with every provider, and model discovery does not prove chat generation or tool calling works. After setup, save settings, test the connection, and verify a real chat/task. Provider billing and usage limits still apply.


## Install J.A.R.V.I.S on Windows, Android, and iOS

> **Important:** Download only from this repository's GitHub Actions artifacts. A workflow artifact is a ZIP download, not a permanent public release. Artifacts may expire (the mobile workflow keeps them for 14 days). The iOS workflow currently performs a build check only; it does **not** provide an installable IPA/TestFlight release.

### 1. Windows — Installer or Portable version

**Option A — Windows Installer (recommended when the installer workflow provides an artifact)**
1. Open the [Windows Installer workflow runs](https://github.com/zobaerio/jarvisai/actions/workflows/windows-installer-build.yml). If that page says the workflow cannot be found, open [all Actions runs](https://github.com/zobaerio/jarvisai/actions/workflows/windows-installer-build.yml) and select the run named **Windows Installer Package**.
2. Open the newest run with a green **Success** status.
3. Scroll to **Artifacts** at the bottom and download the installer artifact (ZIP).
4. Extract the ZIP, then run the included installer file. If Windows SmartScreen warns that the app is unsigned, verify that you downloaded it from this repository before choosing whether to continue. Do not bypass a warning for a file from an unknown source.
5. Follow the installer prompts, then launch **J.A.R.V.I.S** from the Start menu or Desktop shortcut.

**Option B — Portable ZIP (no normal installation required)**
1. Open [all GitHub Actions runs](https://github.com/zobaerio/jarvisai/actions/workflows/windows-portable-build.yml) and select the newest successful **Windows Portable Package** run.
2. Download its portable artifact from the **Artifacts** section.
3. Extract the ZIP to a folder you control (for example, Documents\JARVIS).
4. Open the extracted folder and run the included J.A.R.V.I.S executable. Keep the extracted folder together; do not move only the EXE out of its folder.

**Option C — Run from source**
1. Download the repository using **Code → Download ZIP**, or clone it.
2. Open `Zobaerio-Jarvis-AI/`.
3. Install [Python 3.12.x 64-bit](https://www.python.org/downloads/).
4. Run `install.bat`, then `run.bat`.

If a workflow is still running, has failed, or has no artifact, wait for a successful run or use another available installation method. The Windows installer and portable packages may be unsigned.

### 2. Android — Debug APK

1. Open the [Android build workflow run](https://github.com/zobaerio/jarvisai/actions/runs/40374198718). If the artifact has expired, open [all Actions runs](https://github.com/zobaerio/jarvisai/actions) and choose the newest successful **Mobile Build Validation** run.
2. Open **Artifacts** and download `jarvis-mobile-android-debug` (a ZIP file).
3. On your Android phone, extract the ZIP using Files or another archive app. Find the `.apk` file inside.
4. Tap the APK. If Android asks, allow **Install unknown apps** only for the file manager/browser you used to open the APK, then return and tap **Install**.
5. After installation, open **J.A.R.V.I.S**.

**Security note:** Install only an APK you downloaded from this repository's Actions page. Turn off the temporary “install unknown apps” permission afterward if you enabled it.

**Current limitation:** This is a **debug APK**, not a signed production/release APK or AAB. The mobile app is an early AI chat client; it does not yet have all Windows desktop automation features. You may need a compatible provider API key and internet access to chat with an AI model.

### 3. iOS (iPhone/iPad) — build check only for now

The [mobile workflow](https://github.com/zobaerio/jarvisai/actions) compiles the iOS app without code signing as a CI check. **There is currently no signed IPA, TestFlight invitation, or App Store release linked here**, so you cannot install this build on an iPhone/iPad from the workflow artifact. iOS installation instructions will be added once a signed distribution method is configured.

### Troubleshooting

- **No Artifacts section:** the run may still be in progress, may have failed, or artifact upload may not have completed.
- **Artifact expired:** run a new successful build from GitHub Actions or use another currently available artifact.
- **Windows blocks the installer:** check that it came from this official repository and note that unsigned builds can trigger SmartScreen. Do not run files from untrusted sources.
- **Android says “Can't install app”:** confirm the ZIP was extracted, open the actual APK, ensure the phone has enough free space, and remove an older conflicting debug build if needed.
- **AI does not respond:** check your internet connection, provider/base URL, model name, API key, and provider quota in app settings. Never share your API key publicly.

