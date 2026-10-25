# J.A.R.V.I.S Desktop AI — Windows 11

**J.A.R.V.I.S Desktop AI v1.2.1** is the Windows desktop assistant package for this repository. It includes the Python desktop UI, assistant/tool logic, settings, voice support, installation scripts, and the three character images provided by the owner.

## Restore the complete app package from GitHub
The ZIP is stored as numbered Base64 parts in `bundle/`, so GitHub's text-file upload path can preserve the binary archive. After downloading this repository as a ZIP and extracting it:

1. Run `restore.bat` from the repository root.
2. The script joins parts `01`–`16`, reconstructs `JARVIS-Windows11-v1.2.1.zip`, checks the expected SHA-256, then extracts it to `restored\`.
3. Open `restored\Zobaerio-Jarvis-AI\`.
4. On Windows 11, install [Python 3.12.10 64-bit](https://www.python.org/downloads/release/python-31210/).
5. Run `install.bat`, then `run.bat`.

Expected archive SHA-256:
`766aeb1fdffbd981e91742169f146de9091096468e199d3726f7313524b695d6`

## Characters and animation
The package includes the three original character images supplied in chat as `LUNA` (pink/purple hair), `MAYA` (brown-hair portrait), and `RUBY` (red hair). The prototype's animation is a subtle idle 2.5D effect and best-effort blink overlay. It is not yet a true 3D/skeletal rig, natural hand/leg movement, walking, or production lip-sync. MAYA's supplied source is a portrait, not a full-body drawing.

## AI and safety
Optional local AI via Ollama is supported; the setup notes use `qwen2.5:3b`. The assistant's tool actions are allow-listed. File creation/change asks for confirmation; arbitrary shell execution is not enabled by default. Speech recognition/neural voice features may need internet and may transmit audio or text to their provider.

## Test status
Archive reconstruction is integrity-checked by SHA-256. Python syntax and package ZIP integrity were checked during packaging. The app has not been fully runtime-tested on the target Windows 11 laptop; confirm microphone, speakers, permissions, and each automation action before relying on it.
