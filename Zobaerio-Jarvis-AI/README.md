# J.A.R.V.I.S Desktop AI — Windows 11

**Repository:** https://github.com/zobaerio/jarvisai  
**Owner:** zobaerio  
**Version:** 1.2.0 — User-supplied character gallery

A Python desktop personal-assistant prototype with a dark sci-fi command center, voice input/output, configurable local AI endpoint, allow-listed desktop/web commands, and three selectable character artworks.

## Character gallery

The three source images supplied by the repository owner are stored unchanged at:

- `assets/characters/reference/luna.jpg` — purple-haired full-body character
- `assets/characters/reference/ruby.jpg` — red-haired full-body character
- `assets/characters/reference/maya.jpg` — brown-haired portrait character

The dashboard displays these exact source images and uses an idle 2.5D effect (gentle scale/bob/sway plus a best-effort blink overlay). This is **not a full skeletal or 3D character rig**. In particular, still artwork does not contain enough hidden information to animate individual hands, legs, facial expressions, or walking naturally while keeping every pixel exactly unchanged. True human-like motion needs a rigged model or separately generated animation frames. Maya's provided source is a square portrait, so it cannot show a full body or leg animation without a different asset.

## Requirements

- Windows 11 (Windows 10 may also work)
- Python 3.12.x, 64-bit recommended
- Microphone and speakers/headphones for voice features
- Internet for online speech recognition / Edge TTS; these speech services may transmit audio or text to their providers
- Optional: [Ollama for Windows](https://ollama.com/download/windows) for local LLM responses

Python 3.12 is recommended because PyAudio wheels are commonly available for this interpreter; Python 3.14 may trigger a C++ compilation error.

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
