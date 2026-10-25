# J.A.R.V.I.S Desktop AI — PyInstaller one-folder build.
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve()
datas = [(str(ROOT / "assets"), "assets")]
binaries = []
hiddenimports = [
    "speech_recognition",
    "pyaudio",
    "edge_tts",
    "pygame",
    "keyring",
    "pyttsx3",
    "pyttsx3.drivers.sapi5",
    "pyautogui",
    "pyperclip",
    "send2trash",
    "pystray",
    "pystray._win32",
    "win32com",
    "win32com.client",
    "pythoncom",
    "pywintypes",
    "comtypes",
]

# Several runtime integrations are imported lazily, so collect their metadata
# and platform modules explicitly to avoid "works in Python, fails in EXE" issues.
for package in ("edge_tts", "pygame", "keyring", "pyttsx3", "comtypes"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

for package in ("speech_recognition", "pyautogui"):
    hiddenimports += collect_submodules(package)

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="JARVIS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "build" / "jarvis.ico"),
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="JARVIS",
)
