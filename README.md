# J.A.R.V.I.S Desktop AI — Windows 11

**Latest source:** `Zobaerio-Jarvis-AI/`  
**Version:** 1.2.3 — Procedural 3D Avatar Studio + local rigged GLB import  
**Repository:** https://github.com/zobaerio/jarvisai

The latest readable source tree is committed under `Zobaerio-Jarvis-AI/`. Download/clone this repository, then open that folder and run `install.bat` followed by `run.bat`. Use Python 3.12.x 64-bit on Windows 11.

## New in v1.2.3
- A **OPEN REAL 3D AVATAR STUDIO** button in the desktop dashboard.
- Three.js procedural 3D character meshes for LUNA, RUBY and MAYA with separate body parts, idle motion, waving, blinking and simulated speaking-mouth movement.
- **IMPORT RIGGED .GLB** lets you load a model from your own computer. The browser parses that model locally and does not upload the GLB file.
- Embedded idle/default and named wave/talk clips can be played if they exist inside the imported model.
- A feature inventory and a Bengali guide for generating, rigging and importing your own 3D character.

The built-in characters are stylized procedural models—not photorealistic or 1:1 recreations of the reference drawings. The app does not automatically generate a matching 3D model from those pictures or invent absent animation clips. For close likeness, create/license a rigged GLB with the needed motion clips first. Natural walking, hair/cloth physics, expressive facial rigging and phoneme-level lip-sync remain unfinished. Maya's supplied source is only a portrait and cannot define missing full-body geometry. The viewer loads Three.js from a CDN and needs internet access plus WebGL support.

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
