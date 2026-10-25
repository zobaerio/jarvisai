# J.A.R.V.I.S Desktop AI — Windows 11

**Repository:** https://github.com/zobaerio/jarvisai  
**Owner:** zobaerio  
**Version:** 1.2.2 — Procedural 3D Avatar Studio prototype

A Python desktop personal-assistant prototype with a dark sci-fi command center, voice input/output, configurable local AI endpoint, allow-listed desktop/web commands, three character reference profiles, and a real-time procedural 3D Avatar Studio.

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

## Safety and capabilities

- Only explicitly allow-listed app and website actions are supported by default.
- Creating or changing files requires confirmation in the assistant workflow.
- Arbitrary PowerShell/shell execution is intentionally not exposed as a default tool.
- An AI model may plan only from its configured tools; it cannot literally operate every program or guarantee every task will complete.
- Review any action before allowing it to send messages, submit forms, or alter important files.

## Development checks

Syntax check:

```powershell
python -m compileall -q app.py jarvis
```

The repository owner should also test microphone, speaker output, character selection, and each desktop command on the target Windows 11 machine before treating the project as production-ready.
