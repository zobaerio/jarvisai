# J.A.R.V.I.S Desktop AI — Windows 11

The full source bundle for **J.A.R.V.I.S Desktop AI v1.2.0** is included in the `bundle/` directory as numbered Base64 parts (this keeps the ZIP package transferable through text-only repository APIs).

## Restore and install
1. Download this branch/repository as a ZIP and extract it.
2. Run `restore.bat`. It joins the numbered bundle parts and reconstructs `JARVIS-Windows11-v1.2.0.zip`, then extracts it into `restored\`.
3. Open `restored\Zobaerio-Jarvis-AI\`.
4. Install **Python 3.12 64-bit** from https://www.python.org/downloads/release/python-31210/ .
5. Run `install.bat`, then `run.bat`.

The reconstructed package contains the app source, requirements, installer scripts, and all three character images supplied by the repository owner. Those original JPEGs are stored without pixel edits in `assets/characters/reference/`.

## Character motion — honest scope
LUNA and RUBY are full-body still illustrations; MAYA is a square portrait. The desktop app gives the still art subtle idle 2.5D motion (breathing scale, gentle sway/bob and a brief best-effort blink overlay). It is **not** a full skeletal/3D rig, natural walking animation, or production lip-sync. Maya's image contains no full body or legs to animate. True person-like limb articulation needs a rigged character or animation/video frames.

## AI and permissions
The app supports allow-listed app/site/file tools and an optional local Ollama model. File creation/change asks for confirmation; arbitrary shell execution is not enabled by default. Voice recognition and neural voice may require internet and may transmit audio/text to their providers. Test microphone, speaker output and every action on the target Windows 11 PC before production use.
