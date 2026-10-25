# J.A.R.V.I.S Desktop AI — Feature Status & Production Roadmap

Audit date: 2026-10-25. Version focus: v1.7.3 bounded voice recognition and playback timeouts. This inventory describes code that exists; it does not claim every planned feature is implemented.

## Implemented in the Python desktop prototype
- **Background Mode (system tray):** closing the main window can hide J.A.R.V.I.S to the Windows system tray instead of terminating the process. The tray menu restores the window or explicitly exits. Active tasks continue while hidden; a real exit requests cancellation and warns if a task is active. This is not yet a separate Windows service and does not guarantee tasks survive sign-out or reboot.
- Dark Windows desktop command-center UI with generated J.A.R.V.I.S branding, taskbar/window icon, clock and CPU/memory indicators.
- Responsive desktop layout: the right-side rail hides on narrow windows, decorative top navigation collapses, and the main workspace grows; minimum window size is 820×560.
- Selectable LUNA, RUBY and MAYA reference profiles.
- One-shot microphone input using SpeechRecognition + Google speech recognition (internet required), with bounded network-operation timeout.
- Spoken responses using Edge TTS with pyttsx3 fallback; online synthesis and primary playback paths have bounded timeouts.
- Configurable OpenAI-compatible Chat Completions endpoint; optional local Ollama setup.
- AI tool-call loop for a limited allow-list: launch selected apps, open websites, open common folders, filename search, basic system information, consent-gated text-file read/create, folder creation, and approval-gated single-file copy/move/rename.
- Social web navigation via voice/AI tool calls: open WhatsApp Web, Facebook, YouTube, Instagram and Messenger, plus explicit English/Bangla YouTube search commands.
- Google Workspace navigation: open Gmail, Calendar, Drive, Docs, Sheets and Maps through official URLs using English and selected Bangla aliases; this opens the service only and does not access account data or submit actions.
- WhatsApp message-draft preparation: validate an international phone number and bounded message text, open WhatsApp Web with the message prefilled, and leave final recipient review and sending to the user; the app does not click Send or claim delivery.
- Email draft preparation: validate a single recipient address and bounded subject/body, open the default email app through a `mailto:` draft, and leave final review and sending to the user; this does not authenticate to Gmail/Outlook or send messages.
- Calendar event draft preparation: validate local ISO start/end times, duration, content limits and timezone allow-list, then open a Google Calendar template; it never saves the event or sends invitations automatically.
- Foreground desktop actions: list visible window titles (title-only), paste text into a named Windows window and send allow-listed editing/navigation shortcuts—each interaction requires explicit user approval.
- Deterministic local verification: check whether an exact filename/folder exists inside an allowed user folder or a visible window title matches a target; brief tool outcome lines are persisted to task history.
- Approval dialog for supported file/folder changes; API key stored with keyring when available.
- Approval-gated opening of common document/data/image files through the Windows default app; executable/script extensions, symlinks, traversal, and files changed during confirmation are blocked.
- Consent-gated reading of a selected text file (maximum 100 KB), with exact path/size disclosure, provider-transmission notice, recheck against file changes and binary/symlink blocking.
- Consent-based, bounded local content search for common text/source files; skips symlinks/binary/hidden/ignored directories, caps files and result snippets, and warns that matching excerpts enter the AI conversation.
- Consent-gated duplicate-file detection using local SHA-256 for same-size candidates, bounded to 5,000 entries/256 MiB of hash work, skipping symlinks, hidden/generated directories and files over 100 MiB; returns limited path/hash summaries only and never modifies files.
- Approval-gated bounded ZIP archive creation for up to 100 selected regular files (100 MiB total), with explicit confirmation, per-source identity rechecks, temp-file cleanup, and atomic no-overwrite publishing; unsupported filesystems fail closed.
- Approval-gated single-file copy, move and rename within Desktop/Documents/Downloads; blocks symlinks/path traversal, refuses overwrites, and preserves the source until a destination copy succeeds.
- Opt-in wake-word listening prototype.
- Settings JSON uses atomic fsynced saves and a recovery backup; corrupt primary files fall back to a validated backup. API keys remain outside this file in the credential store.
- Approval-gated file-to-Recycle-Bin action for one regular file inside Desktop/Documents/Downloads, with path/size/type preview, symlink/path traversal/directory blocking and file-change recheck; not a permanent-delete tool.
- Startup recovery marks abandoned running/cancelling tasks failed, preserves queued/terminal tasks, avoids automatic replay, and leaves tasks belonging to a live owner process untouched.
- AI provider error responses are mapped to safe HTTP-status diagnostics; raw response bodies and exception strings are not surfaced. Malformed JSON, choices, message and tool-call payloads are validated to prevent adapter errors escaping the worker.
- Bounded AI provider retries for connection/timeouts and HTTP 408/429/500/502/503/504, with short `Retry-After` handling, a three-attempt maximum and cancellation-aware backoff. Retry occurs before tool execution and never replays a completed desktop/file action.
- Structured per-tool action audit in task history: tool name, lifecycle state and timestamps only; arguments and returned payloads are not copied into audit metadata. If a task is recovered after a process restart, any still-running action is marked `interrupted` with an unknown outcome and is never automatically replayed.
- Explicit task outcome state (`completed`, `partial`, `failed`, `cancelled`) is retained in Task History. Known provider/configuration errors and malformed responses are marked failed; tool exceptions or the bounded action/round budget produce partial status. This is not semantic verification of the user's overall goal.
- Task History exposes an explicit cancel action for a selected `queued` command. It marks that command `cancelled` before execution, does not touch running/terminal tasks, and preserves FIFO order among remaining queued commands.
- Task History can search within the latest 100 records by command, result, progress events, task ID or tool-action metadata, and filter by recorded task status. Filters run locally and do not mutate or execute tasks.
- Task History can export a user-confirmed aggregate diagnostics JSON with task/action counts, UTC dates/durations and runtime version fields. The report excludes user command/result text, IDs, paths, progress text, tool names/arguments/results and exception details.
- Task History can export one selected task record as JSON after an explicit privacy warning and confirmation. This detailed export can include command/result/progress text and file paths; the separate aggregate Safe Diagnostics export remains content-free.
- Unexpected tool/worker exception text is redacted from user/provider-facing responses; only the sanitized exception type and generic guidance are emitted. Progress telemetry records the tool name/status, not the returned tool-result text.
- AI endpoint validation rejects embedded URL credentials/query fragments and blocks API-key transmission over remote plain HTTP; Settings exposes a background /models connectivity check without a chat-generation request.
- Persistent local task history (latest 100 tasks), including command, status, timestamps, result summary and bounded progress events; path-level in-process locking, unique temp files, fsync/atomic replacement and backup recovery; history viewer is available in the desktop UI.
- Manual retry of a selected historical command after an explicit confirmation; a retry creates a fresh task record.
- Persistent FIFO command queue: commands can be queued while another task runs; the user can arm saved queued commands after a restart.
- Cooperative cancellation between AI request/tool steps; the approval dialog also offers a Cancel Task action.
- New 3D Character Studio prototype: Three.js builds genuine 3D meshes with separate head/torso/upper arms/forearms/thighs/lower legs and eyes, plus idle motion, waving, periodic blink and simulated speech-mouth motion. Startup/import and renderer initialization failures now show a readable recovery panel with a reload action instead of leaving a blank preview; WebGL context loss is reported to the user.

## Prototype / partial
- 3D design: stylized procedural mesh characters inspired by the references, not photorealistic or a pixel-perfect 1:1 conversion. The viewer now accepts a user-selected local rigged `.glb` model and can play embedded animation clips.
- Animation: procedural characters have independent limb parts and simulated motion. A user-provided rigged `.glb` can replace the selected procedural character; if the file contains embedded clips, the viewer can play an idle/default clip and clips named like wave/hello/gesture or talk/speak. There is still no built-in production skeletal rig, generated custom model, hair/cloth physics, motion capture, natural walking, emotion capture or phoneme-level lip-sync.
- 3D viewer runs in the default browser via a loopback-only HTTP server. Three.js 0.186.1 loads from a CDN, so an internet connection and WebGL-compatible browser are required. CDN or renderer startup failures display a recovery panel; actual GPU/browser recovery still requires device-level testing.
- Wake word is based on repeated speech recognition, not a dedicated low-latency offline wake-word engine.
- AI Agent can plan only with declared tools. Foreground controls are limited to title-matched text paste and a small shortcut allow-list with approval; there is no screenshot/OCR context, arbitrary clicking, broad keyboard scripting, or guaranteed completion of multi-app workflows.
- Cancellation is cooperative, not a forced process kill: a blocking model network read may continue until the 45-second read timeout, and an already-started desktop/external action cannot be undone.
- System telemetry covers CPU/memory, not a full GPU/temperature/hardware health suite.
- Settings and permissions are basic; there is no roles/teams/account system.
- An unsigned Windows one-folder portable package is now defined by a PyInstaller spec, isolated build script, and Windows GitHub Actions artifact workflow. It is not code-signed, is not MSIX, and has no built-in updater. The package includes `version.json`, and CI verifies the manifest matches the central source version.
- An interactive local system-health dialog reports Python/OS compatibility, required 3D/branding assets, dependency availability and AI endpoint/model configuration presence without sending network requests or displaying endpoint/API-key values. For cloud endpoints it also detects whether a key is available through secure storage; it never displays the key, and local endpoints do not require one.
- The UI is responsive for resizable desktop windows; this release is not yet a mobile/phone app and has no Android installer.

## Not implemented yet
- Custom rigged GLB/VRM assets that match the supplied character designs closely are not bundled; the new import button only loads a model the user already has. Asset ownership/licensing must be confirmed.
- Natural humanoid motion, realistic hands/fingers, expressions, eye gaze, proper talking animation and real lip-sync.
- Screen understanding with screenshot/accessibility-tree context and safe interaction with arbitrary applications.
- Full integrations for Gmail/Outlook, Office document editing or calendar account access, Facebook reactions/comments, automated WhatsApp sending, phone calls, or form submission. Calendar currently opens a prefilled event template for the user to review and save manually; WhatsApp opens a prefilled message for the user to review and send manually.
- Multi-step AI plans with durable per-step state, automatic retry/backoff policies, resume of a partially executed task after restart, and semantic verification that the user's overall goal was achieved. Current verification checks only local file/folder existence and visible window titles, not the contents/quality of a document or whether an external task is fully complete.
- Fully offline speech recognition/TTS, bundled local LLM, native signed EXE/MSIX installer, app auto-update, rollback and crash reporting.
- Automated Windows 11 hardware QA for actual microphones, speakers, WebGL/GPU acceleration, wake listening and each action.

## Delivery order
1. Stabilize the updated source tree and install workflow; run a clean install on Windows 11.
2. Verify WebGL/CDN failure handling and connect character/task state from the desktop app to the browser studio.
3. Build/license custom GLB/VRM models matching the supplied characters, embed idle/wave/talk clips, add facial rigging and phoneme lip-sync.
4. Extend the FIFO command queue into a durable multi-step task planner with automatic retries/backoff, resume-after-restart, explicit step approvals and verified action logs.
5. Add one scoped Office/calendar/email integration at a time, using least-privilege permissions and confirmation before sending/submitting.
6. Add screen-aware automation after threat modelling, allowlists, action confirmations and audit logging.
7. Add automated tests, CI, signed package, uninstaller, updater and repeatable device-level tests.

## Voice reliability limitations
- Speech recognition still uses an online provider by default; the timeout limits waiting but does not make recognition offline.
- Local TTS fallback is best-effort and depends on Windows audio drivers and installed voices; device-level microphone/speaker QA remains required.

## Safety/privacy
The assistant cannot safely promise to do “everything.” Keep automation least-privilege and require approval for meaningful external or destructive actions. Do not commit API keys or credentials. Stored provider keys must not be sent over plain HTTP to non-loopback endpoints. Online speech recognition and neural TTS may transmit audio/text to their providers. The 3D Studio preview itself does not request camera or microphone access. Task history is stored locally as JSON under the app's APPDATA folder and is not encrypted by this feature; an atomic-save backup aids recovery but does not replace encrypted storage; avoid entering passwords, API keys or other secrets as commands.
