# J.A.R.V.I.S Desktop AI — Windows 11

**Latest source:** `Zobaerio-Jarvis-AI/`  
**Version:** 1.2.2 — Procedural 3D Avatar Studio prototype  
**Repository:** https://github.com/zobaerio/jarvisai

The latest readable source tree is committed under `Zobaerio-Jarvis-AI/`. Download/clone the repository, then open that folder and run `install.bat` followed by `run.bat`. Use Python 3.12.x 64-bit on Windows 11.

## New in v1.2.2
- A new **OPEN REAL 3D AVATAR STUDIO** button in the desktop dashboard.
- Three.js procedural 3D character meshes for LUNA, RUBY and MAYA with separate body parts, idle motion, waving, blinking and simulated speaking mouth movement.
- A feature inventory that marks the implemented, partial and not-yet-implemented features.

The 3D characters are real 3D meshes, but they are still stylized procedural approximations—not 1:1 photorealistic recreations of the reference drawings. Production-quality rigged GLB/VRM models, natural walking, hair/cloth physics and phoneme-level lip-sync remain unfinished. The 3D viewer loads Three.js from a CDN and needs an internet connection plus WebGL support.

## Install and test
1. Download this repository (or clone it) and open `Zobaerio-Jarvis-AI/`.
2. Install [Python 3.12.10 64-bit](https://www.python.org/downloads/release/python-31210/).
3. Run `install.bat`, then `run.bat`.
4. Click **OPEN REAL 3D AVATAR STUDIO** in the desktop app.
5. Review `Zobaerio-Jarvis-AI/FEATURE_STATUS.md` before assuming a feature exists.

## Legacy package
The `bundle/` folder and root `restore.bat` preserve the previous v1.2.1 archive for reproducibility. That archived ZIP does not contain the v1.2.2 3D studio update; use the current source directory above for v1.2.2.

## Safety and QA
Only allow-listed desktop tools are enabled by default; supported file/folder changes ask for approval. Voice services may transmit audio/text to their providers. A syntax check and local HTTP smoke test passed during development, but target-device WebGL/GPU, microphone and speaker tests have not yet been completed.
