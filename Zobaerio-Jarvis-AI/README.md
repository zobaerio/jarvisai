# J.A.R.V.I.S Desktop AI — Windows 11

**Repository:** https://github.com/zobaerio/jarvisai  
**Owner:** zobaerio  
**Version:** 1.6.4 — Honest task outcome status

A Python desktop personal-assistant prototype with a dark sci-fi command center, voice input/output, configurable local AI endpoint, allow-listed desktop/web commands, three character reference profiles, and a real-time procedural 3D Avatar Studio.

## Branding and responsive layout

The official brand source lives in `assets/branding/jarvis-mark.svg` and `assets/branding/jarvis-wordmark.svg`. On installation/startup, `jarvis/branding.py` uses the existing Pillow dependency to generate a PNG logo and multi-size Windows ICO under `%APPDATA%\Zobaerio\Jarvis\`. The installer assigns that ICO to the Desktop shortcut, and the app uses the same mark in the window icon and header.

The desktop window can resize down to 820×560. Below 1180 px the right-hand utility rail collapses to give the agent workspace more room; below 1120 px decorative top navigation labels hide. This is responsive desktop behavior, not a mobile/Android build. Phone installation remains a later platform phase.

## Character gallery

The three source images supplied by the repository owner are stored unchanged at:

- `assets/characters/reference/luna.jpg` — purple-haired full-body character
- `assets/characters/reference/ruby.jpg` — red-haired full-body character
- `assets/characters/reference/maya.jpg` — brown-haired portrait character

The selector cards retain the user-supplied images as reference thumbnails. The main dashboard no longer pretends the flat artwork is a 3D person. Click **OPEN REAL 3D AVATAR STUDIO** to open a separate browser-based viewer that builds actual 3D meshes and animates the head, torso, upper/lower arms, thighs, lower legs, eye blinks and a simulated speaking mouth. These are stylized procedural 3D approximations inspired by LUNA/RUBY/MAYA, not photorealistic or pixel-perfect 1:1 reconstructions. Maya's source is only a portrait, so it cannot provide hidden full-body details for an exact 3D reconstruction.

## Requirements

- Windows 11 (Windows 10 may also work)
- Python 3.12.x, 64-bit recommended
- Microphone and speakers/headphones for voice features
- Internet for online speech recognition / Edge TTS; these speech services may transmit audio or text to their providers
- Optional: [Ollama for Windows](https://ollama.com/download/windows) for local LLM responses

Python 3.12 is recommended because PyAudio wheels are commonly available for this interpreter; Python 3.14 may trigger a C++ compilation error.

## 3D Character Studio (prototype)

The desktop app's **OPEN REAL 3D AVATAR STUDIO** button launches `assets/avatar_studio.html` via a loopback-only local HTTP server. It renders separate 3D mesh parts; it does not animate the original image as a flat plane. Drag to orbit, scroll to zoom, switch characters, pause idle motion, play a wave and trigger browser speech.

Three.js 0.186.1 loads from jsDelivr at runtime, so internet access and a WebGL-compatible browser are required for the viewer. The source assets are reference images only. Click **IMPORT RIGGED .GLB** to select a local binary GLB; that model replaces the currently selected procedural character. The Studio plays a default/idle clip if present and offers wave/talk controls for embedded clips with matching names. File parsing happens locally in the browser; the model is not uploaded. The app does not create a custom rig or add animations that aren't present in the GLB. Realistic hair/cloth physics, custom model creation and phoneme-level lip-sync are not included.

See `FEATURE_STATUS.md` for what is implemented, partial and still planned.

For the end-to-end image → 3D model → rig → GLB import process, see [3D_CHARACTER_PIPELINE_BN.md](3D_CHARACTER_PIPELINE_BN.md).

## Install and run

1. Install Python 3.12 (64-bit) from https://www.python.org/downloads/release/python-31210/.
2. Extract or clone this repository into a normal writable folder.
3. Double-click `install.bat` and allow it to create `.venv` and install requirements.
4. Double-click `run.bat` to open J.A.R.V.I.S.
5. Choose LUNA, RUBY, or MAYA on the left. The selected personality updates the preferred speech voice.
6. For local LLM support, install Ollama, run `ollama pull qwen2.5:3b`, then configure `http://localhost:11434/v1` and model `qwen2.5:3b` in Settings.

If installation fails, open PowerShell in the project folder and run `python --version`, then share the full installation error. Do not run `python pip install ...`; use `python -m pip install ...`.

## Safe Recycle Bin action

J.A.R.V.I.S can send one regular file from Desktop, Documents or Downloads to the Windows Recycle Bin. It displays the exact path, size and type and asks for approval. It rejects directories, symbolic links, path traversal, missing files and files that change while the approval dialog is open. This is a recoverable OS trash operation, not a permanent-delete command; recovery still depends on the Recycle Bin not having been emptied and Windows permitting the move.

## Safe duplicate-file finder

J.A.R.V.I.S can find identical files by locally hashing same-size candidates in Desktop, Documents, Downloads or all three. The scan requires approval, is limited to 5,000 file entries and 256 MiB of total hashing, skips individual files over 100 MiB, hidden/generated directories, symbolic links and files that change during hashing. Only matching paths, sizes and shortened hash fingerprints enter the AI conversation; file contents are not included, and no file is modified or deleted. The tool does not decide which copy should be removed.

## Safe ZIP archive creation

J.A.R.V.I.S can create a ZIP from 1–100 selected regular files in a single allow-listed folder (Desktop, Documents or Downloads), up to 100 MiB total uncompressed size. The approval dialog lists the archive name and every selected source filename/size. Path traversal, symbolic links, directories, duplicate entry names, existing destination files and source files that change after approval are blocked. The ZIP is published with an atomic no-overwrite operation on filesystems that support same-directory hard links; otherwise the operation fails closed. Original files remain unchanged.

## Startup recovery for interrupted tasks

At startup, J.A.R.V.I.S checks persisted task history. Tasks left in a running/cancelling state from a process that is no longer active are marked failed with a recovery note and a timestamp. They are not automatically replayed because desktop/file actions may already have partially occurred; the user must review Task History before retrying. Queued tasks remain queued and are never started automatically during recovery. Tasks belonging to a process that still appears active are left untouched.

## Safe AI provider error handling

Provider HTTP error bodies are no longer echoed into the conversation because a provider or proxy could reflect private prompts, file excerpts or credentials. J.A.R.V.I.S maps common HTTP statuses to safe, actionable messages instead. It also validates the outer JSON/choices/message/tool-call shapes and returns a bounded, neutral diagnostic for malformed responses. Unexpected request/library errors are reduced to their exception type; their raw message and response body are not exposed to the user.

## AI endpoint validation and connection test

Settings validates the API base URL, rejects embedded URL credentials and query/fragment components, and prevents the assistant from sending a stored API key over plain HTTP to a non-local endpoint. Use HTTPS for remote providers; loopback addresses such as localhost can use HTTP for local services.

**Test Connection** sends a GET request to `/models` only. It does not submit a chat prompt or generate an answer. The result confirms reachability and whether the configured model appears in the returned list; it does not prove that chat completions or tool-calling work with every provider.

## Durable settings storage

Settings are written through a unique same-directory temporary file, flush/fsync and atomic replace. A local `settings.json.bak` recovery copy is refreshed after a successful save; if the primary settings file is unreadable, J.A.R.V.I.S attempts to load the backup. This helps avoid partial JSON after an interrupted save, but does not encrypt settings or replace normal device backups. API keys remain in the Windows credential store, not in this JSON file.

## Task history and cancellation (v1.3.0)

The right-side **ACTIVE TASKS** panel now includes **RUN QUEUED TASKS**, **CANCEL CURRENT TASK** and **TASK HISTORY**. J.A.R.V.I.S keeps the newest 100 task records, including the command, status, timestamps, result summary and progress events. While a task is running, you can type another command and press **QUEUE**; J.A.R.V.I.S asks before saving it to the FIFO queue. Armed queue entries run one at a time after the active task finishes, with the normal file/folder approval checks still in place. Select a row and use **Retry Selected Task** to run its saved command again after a confirmation warning; it uses current settings and creates a new record. File/folder approval dialogs include a **Cancel Task** option.

Cancellation is cooperative. An already-blocked model request may need to finish before cancellation is observed (the network read timeout is 45 seconds); a desktop or external action that already started cannot be automatically undone. The assistant will avoid starting subsequent AI tool actions after it observes cancellation.

Task history and queued commands are stored locally in `%APPDATA%\Zobaerio\Jarvis\task_history.json`. The JSON is not encrypted by this feature. Task-history saves use unique temporary files, flush/fsync and atomic replacement; `task_history.json.bak` is a recovery copy if the primary JSON becomes unreadable. This reduces corruption/lost-update risk but is not a substitute for encrypted storage or regular backups. After restarting the app, saved queued commands do not run automatically; press **RUN QUEUED TASKS** and confirm to resume them. Do not use commands to store passwords, API keys or other secrets.

## Consent-gated reading of a specific file

Before reading any supported text/source file, J.A.R.V.I.S shows the exact path and size and asks for explicit approval. The dialog warns that the file contents enter the AI conversation and may be sent to the configured AI provider. Reading is limited to supported text formats up to 100 KB; symbolic links, binary/null-byte files and files that change during confirmation or reading are blocked. Declining means no file content is returned.

## Consent-based local content search

J.A.R.V.I.S can search inside common text and source-code files in Desktop, Documents, Downloads or all three locations. Before scanning, it asks for approval and explains that up to 20 short matching-line excerpts enter the AI conversation and may be sent to the configured provider. The search skips hidden/ignored directories, symbolic links, binary files and files larger than 256 KB. It scans at most 5,000 files and does not edit any file. This is a bounded text search, not full-disk search or semantic document verification.

## Approved file opening

J.A.R.V.I.S can open a selected document, data file or image from Desktop, Documents or Downloads with the Windows default application after showing the exact path, format and size in an approval dialog. It blocks scripts and executables, symbolic links, path traversal, and files that change while the approval dialog is open. The response confirms that Windows was asked to open the file; the app still needs to be checked visually.

## Approved file copy, move and rename

J.A.R.V.I.S can copy, move or rename one regular file at a time inside Desktop, Documents and Downloads. Before every operation, an approval dialog shows the exact source, destination, file size and operation. Existing destination files are never overwritten. Symbolic links and path traversal are blocked. Move/rename copies the file first and removes the original only after the destination copy succeeds; if source removal fails, both copies remain and the result reports that partial state. This feature does not delete files, recursively copy folders, or operate outside the three allow-listed locations.

## Approved foreground application actions

The agent can list visible application window titles, paste text into a named window, send a small allow-list of editing/navigation shortcuts, and verify basic outcomes such as whether a file/folder exists or a matching window title is visible. Every paste or shortcut asks for approval and names the target window; the paste action does not press Enter or submit a form. `Enter`, `Alt+F4`, `Windows+R` and arbitrary shortcut sequences are blocked. Text insertion is not independently verified, so check the target app after the action.

This is not full visual computer control. The agent cannot see screenshots or arbitrary app contents, and it does not have general-purpose mouse clicking. Verification is limited to file/folder existence and window titles; it does not validate document contents or prove that an overall external task succeeded. Keep the intended application/window visible and enter a distinctive window-title fragment when the model asks for a target.

## Safety and capabilities

- Only explicitly allow-listed app and website actions are supported by default.
- Creating, copying, moving or renaming files requires action-specific confirmation in the assistant workflow. Existing destination files are never overwritten.
- Arbitrary PowerShell/shell execution is intentionally not exposed as a default tool.
- An AI model may plan only from its configured tools; it cannot literally operate every program or guarantee every task will complete.
- Review any action before allowing it to send messages, submit forms, or alter important files.

## Development checks

Syntax check:

```powershell
python -m compileall -q app.py jarvis tests
```

The repository owner should also test microphone, speaker output, character selection, and each desktop command on the target Windows 11 machine before treating the project as production-ready.


## AI provider retry behavior

Transient provider connection failures and HTTP 408, 429, 500, 502, 503 or 504 responses receive up to two bounded retries before any returned tool action runs. Short `Retry-After` values are respected; longer values return a safe provider error instead of retrying early. Cancel is checked during retry waits. Tool actions are never automatically replayed by this retry layer.


## Tool-action audit history

Task History records each declared tool action as `RUNNING`, `RESULT_RECEIVED`, `FAILED` or `INTERRUPTED`. The audit stores tool names, timestamps and a bounded diagnostic note only; it does not copy tool arguments or result payloads. If the app restarts while a tool is running, recovery marks the outcome unknown and does not automatically replay the action.


## Honest task outcome status

Task History distinguishes `COMPLETED`, `PARTIAL`, `FAILED` and `CANCELLED`. Known provider/configuration failures and malformed responses are marked failed; tool exceptions and execution-budget limits are marked partial. This status reflects known execution signals and is not semantic proof that an overall user goal or document quality has been achieved.
