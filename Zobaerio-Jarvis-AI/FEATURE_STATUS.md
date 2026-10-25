# J.A.R.V.I.S Desktop AI — Feature Status & Production Roadmap

Audit date: 2026-10-25. Version focus: v1.5.6 durable settings persistence and recovery. This inventory describes code that exists; it does not claim every planned feature is implemented.

## Implemented in the Python desktop prototype
- Dark Windows desktop command-center UI with generated J.A.R.V.I.S branding, taskbar/window icon, clock and CPU/memory indicators.
- Responsive desktop layout: the right-side rail hides on narrow windows, decorative top navigation collapses, and the main workspace grows; minimum window size is 820×560.
- Selectable LUNA, RUBY and MAYA reference profiles.
- One-shot microphone input using SpeechRecognition + Google speech recognition (internet required).
- Spoken responses using Edge TTS with pyttsx3 fallback.
- Configurable OpenAI-compatible Chat Completions endpoint; optional local Ollama setup.
- AI tool-call loop for a limited allow-list: launch selected apps, open websites, open common folders, filename search, basic system information, consent-gated text-file read/create, folder creation, and approval-gated single-file copy/move/rename.
- Foreground desktop actions: list visible window titles (title-only), paste text into a named Windows window and send allow-listed editing/navigation shortcuts—each interaction requires explicit user approval.
- Deterministic local verification: check whether an exact filename/folder exists inside an allowed user folder or a visible window title matches a target; brief tool outcome lines are persisted to task history.
- Approval dialog for supported file/folder changes; API key stored with keyring when available.
- Approval-gated opening of common document/data/image files through the Windows default app; executable/script extensions, symlinks, traversal, and files changed during confirmation are blocked.
- Consent-gated reading of a selected text file (maximum 100 KB), with exact path/size disclosure, provider-transmission notice, recheck against file changes and binary/symlink blocking.
- Consent-based, bounded local content search for common text/source files; skips symlinks/binary/hidden/ignored directories, caps files and result snippets, and warns that matching excerpts enter the AI conversation.
- Approval-gated single-file copy, move and rename within Desktop/Documents/Downloads; blocks symlinks/path traversal, refuses overwrites, and preserves the source until a destination copy succeeds.
- Opt-in wake-word listening prototype.
- Settings JSON uses atomic fsynced saves and a recovery backup; corrupt primary files fall back to a validated backup. API keys remain outside this file in the credential store.
- AI endpoint validation rejects embedded URL credentials/query fragments and blocks API-key transmission over remote plain HTTP; Settings exposes a background /models connectivity check without a chat-generation request.
- Persistent local task history (latest 100 tasks), including command, status, timestamps, result summary and bounded progress events; path-level in-process locking, unique temp files, fsync/atomic replacement and backup recovery; history viewer is available in the desktop UI.
- Manual retry of a selected historical command after an explicit confirmation; a retry creates a fresh task record.
- Persistent FIFO command queue: commands can be queued while another task runs; the user can arm saved queued commands after a restart.
- Cooperative cancellation between AI request/tool steps; the approval dialog also offers a Cancel Task action.
- New 3D Character Studio prototype: Three.js builds genuine 3D meshes with separate head/torso/upper arms/forearms/thighs/lower legs and eyes, plus idle motion, waving, periodic blink and simulated speech-mouth motion.

## Prototype / partial
- 3D design: stylized procedural mesh characters inspired by the references, not photorealistic or a pixel-perfect 1:1 conversion. The viewer now accepts a user-selected local rigged `.glb` model and can play embedded animation clips.
- Animation: procedural characters have independent limb parts and simulated motion. A user-provided rigged `.glb` can replace the selected procedural character; if the file contains embedded clips, the viewer can play an idle/default clip and clips named like wave/hello/gesture or talk/speak. There is still no built-in production skeletal rig, generated custom model, hair/cloth physics, motion capture, natural walking, emotion capture or phoneme-level lip-sync.
- 3D viewer runs in the default browser via a loopback-only HTTP server. Three.js 0.186.1 loads from a CDN, so an internet connection and WebGL-compatible browser are required.
- Wake word is based on repeated speech recognition, not a dedicated low-latency offline wake-word engine.
- AI Agent can plan only with declared tools. Foreground controls are limited to title-matched text paste and a small shortcut allow-list with approval; there is no screenshot/OCR context, arbitrary clicking, broad keyboard scripting, or guaranteed completion of multi-app workflows.
- Cancellation is cooperative, not a forced process kill: a blocking model network read may continue until the 45-second read timeout, and an already-started desktop/external action cannot be undone.
- System telemetry covers CPU/memory, not a full GPU/temperature/hardware health suite.
- Settings and permissions are basic; there is no roles/teams/account system.
- The UI is responsive for resizable desktop windows; this release is not yet a mobile/phone app and has no Android installer.

## Not implemented yet
- Custom rigged GLB/VRM assets that match the supplied character designs closely are not bundled; the new import button only loads a model the user already has. Asset ownership/licensing must be confirmed.
- Natural humanoid motion, realistic hands/fingers, expressions, eye gaze, proper talking animation and real lip-sync.
- Screen understanding with screenshot/accessibility-tree context and safe interaction with arbitrary applications.
- Full integrations for Gmail/Outlook, Office document editing, calendar, social media, message sending or form submission.
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

## Safety/privacy
The assistant cannot safely promise to do “everything.” Keep automation least-privilege and require approval for meaningful external or destructive actions. Do not commit API keys or credentials. Stored provider keys must not be sent over plain HTTP to non-loopback endpoints. Online speech recognition and neural TTS may transmit audio/text to their providers. The 3D Studio preview itself does not request camera or microphone access. Task history is stored locally as JSON under the app's APPDATA folder and is not encrypted by this feature; an atomic-save backup aids recovery but does not replace encrypted storage; avoid entering passwords, API keys or other secrets as commands.
