# J.A.R.V.I.S Desktop AI — Feature Status & Production Roadmap

Audit date: 2026-10-25. This inventory describes code that exists; it does not claim every planned feature is implemented.

## Implemented in the Python desktop prototype
- Dark Windows desktop command-center UI, clock and CPU/memory indicators.
- Selectable LUNA, RUBY and MAYA reference profiles.
- One-shot microphone input using SpeechRecognition + Google speech recognition (internet required).
- Spoken responses using Edge TTS with pyttsx3 fallback.
- Configurable OpenAI-compatible Chat Completions endpoint; optional local Ollama setup.
- AI tool-call loop for a limited allow-list: launch selected apps, open websites, open common folders, filename search, basic system information, safe text-file read/create and folder creation.
- Approval dialog for supported file/folder changes; API key stored with keyring when available.
- Opt-in wake-word listening prototype.
- New 3D Character Studio prototype: Three.js builds genuine 3D meshes with separate head/torso/upper arms/forearms/thighs/lower legs and eyes, plus idle motion, waving, periodic blink and simulated speech-mouth motion.

## Prototype / partial
- 3D design: stylized procedural mesh characters inspired by the references, not photorealistic or a pixel-perfect 1:1 conversion.
- Animation: separate limb parts animate, but no production-grade skeletal rig, hair/cloth physics, motion capture, natural walking cycle, emotion capture or phoneme-level lip-sync.
- 3D viewer runs in the default browser via a loopback-only HTTP server. Three.js 0.186.1 loads from a CDN, so an internet connection and WebGL-compatible browser are required.
- Wake word is based on repeated speech recognition, not a dedicated low-latency offline wake-word engine.
- AI Agent can plan only with declared tools; no general screen vision, arbitrary mouse/keyboard automation, or guaranteed completion of multi-app workflows.
- System telemetry covers CPU/memory, not a full GPU/temperature/hardware health suite.
- Settings and permissions are basic; there is no roles/teams/account system.

## Not implemented yet
- Custom rigged GLB/VRM assets that match the supplied character designs closely; asset ownership/licensing must be confirmed.
- Natural humanoid motion, realistic hands/fingers, expressions, eye gaze, proper talking animation and real lip-sync.
- Screen understanding with screenshot/accessibility-tree context and safe interaction with arbitrary applications.
- Full integrations for Gmail/Outlook, Office document editing, calendar, social media, message sending or form submission.
- Durable task plan/queue, cancellation, retries, resumable execution, persistent history and step-by-step result verification.
- Fully offline speech recognition/TTS, bundled local LLM, native signed EXE/MSIX installer, app auto-update, rollback and crash reporting.
- Automated Windows 11 hardware QA for actual microphones, speakers, WebGL/GPU acceleration, wake listening and each action.

## Delivery order
1. Stabilize the updated source tree and install workflow; run a clean install on Windows 11.
2. Verify WebGL/CDN failure handling and connect character/task state from the desktop app to the browser studio.
3. Replace procedural characters with licensed custom rigged GLB/VRM models; add facial rigging and phoneme lip-sync.
4. Add a task planner with explicit step approvals, cancellation, retries, persistence and verified action logs.
5. Add one scoped Office/calendar/email integration at a time, using least-privilege permissions and confirmation before sending/submitting.
6. Add screen-aware automation after threat modelling, allowlists, action confirmations and audit logging.
7. Add automated tests, CI, signed package, uninstaller, updater and repeatable device-level tests.

## Safety/privacy
The assistant cannot safely promise to do “everything.” Keep automation least-privilege and require approval for meaningful external or destructive actions. Do not commit API keys or credentials. Online speech recognition and neural TTS may transmit audio/text to their providers. The 3D Studio preview itself does not request camera or microphone access.
