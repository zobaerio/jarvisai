# J.A.R.V.I.S Desktop AI — Windows 11

This branch documents the v1.2.0 character update for the J.A.R.V.I.S Windows desktop assistant.

## Character update
The app package prepared for this update uses the three reference images supplied by the repository owner:
- **LUNA** — purple-haired full-body still artwork
- **RUBY** — red-haired full-body still artwork
- **MAYA** — brown-haired square portrait

The local Windows project ZIP has these exact source JPEGs under `assets/characters/reference/`, the Python desktop app, requirements, `install.bat`, and `run.bat`.

## Motion limitations
The current desktop prototype uses an idle 2.5D effect (breathing scale, gentle sway/bob, and a best-effort blink overlay). It is not yet a full skeletal/3D rig, natural hand/leg animation, walking, or production lip-sync. Maya's original is a square portrait with no full body to animate. For realistic articulated movement while preserving the supplied art, the characters need a proper rig or separately generated animation frames.

## Setup
Use Python 3.12 (64-bit) on Windows 11, then run `install.bat` and `run.bat` from the project folder. Optional local AI is supported through Ollama with model `qwen2.5:3b`.

**Repository status:** the full binary project package and portrait assets have not yet been committed as ordinary source files on this branch. The working ZIP package is available in the current ChatGPT conversation attachment. This branch is documentation-only and should not be merged as the application implementation.
