from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "Zobaerio" / "Jarvis"
SETTINGS_FILE = APP_DIR / "settings.json"
KEYRING_SERVICE = "Zobaerio.JarvisDesktop"
DEFAULTS: dict[str, Any] = {
    "api_base_url": "http://localhost:11434/v1",
    "model": "qwen2.5:3b",
    "speech_language": "bn-BD",
    "voice": "bn-BD-NabanitaNeural",
    "speak_replies": True,
    "selected_character": "luna",
}


def load_settings() -> dict[str, Any]:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    data = DEFAULTS.copy()
    if SETTINGS_FILE.exists():
        try:
            loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update({k: v for k, v in loaded.items() if k in DEFAULTS})
        except (OSError, json.JSONDecodeError):
            pass
    return data


def save_settings(data: dict[str, Any]) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    safe = {k: data.get(k, DEFAULTS[k]) for k in DEFAULTS}
    SETTINGS_FILE.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")


def get_api_key() -> str:
    try:
        import keyring
        return keyring.get_password(KEYRING_SERVICE, "api_key") or ""
    except Exception:
        return ""


def set_api_key(value: str) -> bool:
    try:
        import keyring
        if value:
            keyring.set_password(KEYRING_SERVICE, "api_key", value)
        else:
            try:
                keyring.delete_password(KEYRING_SERVICE, "api_key")
            except Exception:
                pass
        return True
    except Exception:
        return False
