from __future__ import annotations

import ipaddress
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

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


LOCAL_API_HOSTS = {"localhost"}


def validate_api_base_url(base_url: str) -> str:
    """Validate an OpenAI-compatible base URL without accepting embedded credentials."""
    value = str(base_url or "").strip()
    if not value or len(value) > 2048 or any(ord(char) < 32 for char in value):
        raise ValueError("Enter a valid API base URL (maximum 2,048 characters).")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("The API base URL has an invalid host or port.") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        raise ValueError("API base URL must use http:// or https:// and include a hostname.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Do not place usernames or API keys inside the URL; use the protected API key field.")
    if parsed.query or parsed.fragment:
        raise ValueError("API base URL must not contain query parameters or a fragment.")
    return value.rstrip("/")


def is_local_api_endpoint(base_url: str) -> bool:
    """Recognize actual loopback hosts, not URLs that merely contain the word localhost."""
    parsed = urlsplit(validate_api_base_url(base_url))
    hostname = (parsed.hostname or "").casefold()
    if hostname in LOCAL_API_HOSTS:
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def validate_api_key_transport(base_url: str, api_key: str = "") -> str:
    """Refuse to send a stored API key over plain HTTP to a non-loopback server."""
    normalized = validate_api_base_url(base_url)
    parsed = urlsplit(normalized)
    if api_key and parsed.scheme.lower() == "http" and not is_local_api_endpoint(normalized):
        raise ValueError("API keys are blocked over plain HTTP to non-local endpoints. Use HTTPS or a local endpoint.")
    return normalized


def test_api_connection(
    base_url: str,
    model: str,
    api_key: str = "",
    *,
    timeout: float = 7.0,
) -> dict[str, Any]:
    """Check the non-generative /models endpoint; never sends a chat prompt or logs the key."""
    model_name = str(model or "").strip()
    if not model_name:
        return {"ok": False, "message": "Enter a model name before testing the connection."}
    try:
        normalized = validate_api_key_transport(base_url, api_key)
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        import requests
        response = requests.get(
            normalized + "/models",
            headers=headers,
            timeout=(3, max(1.0, min(float(timeout), 10.0))),
        )
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Could not reach the endpoint ({type(exc).__name__}). Check the URL and confirm that the service is running.",
        }
    status = int(getattr(response, "status_code", 0) or 0)
    if status in {401, 403}:
        return {"ok": False, "status_code": status, "message": f"Endpoint returned HTTP {status}. Check API-key permissions."}
    if status != 200:
        return {
            "ok": False,
            "status_code": status,
            "message": f"/models returned HTTP {status}. Check the API base URL and provider compatibility. No chat generation request was sent.",
        }
    try:
        payload = response.json()
    except Exception:
        return {
            "ok": False,
            "status_code": status,
            "message": "Endpoint responded, but /models did not return valid JSON. Check OpenAI-compatible API support.",
        }
    records = payload.get("data", []) if isinstance(payload, dict) else []
    model_ids = [
        item["id"] for item in records
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ] if isinstance(records, list) else []
    if not model_ids:
        return {
            "ok": True, "model_available": None, "status_code": status,
            "message": "Endpoint reachable (HTTP 200), but no model IDs were listed. This checks connectivity only.",
        }
    if model_name in model_ids:
        return {
            "ok": True, "model_available": True, "status_code": status,
            "message": f"Connected (HTTP 200). Configured model '{model_name}' was listed. No chat generation request was sent.",
        }
    return {
        "ok": True, "model_available": False, "status_code": status,
        "message": f"Endpoint reachable (HTTP 200), but configured model '{model_name}' was not listed. Verify the model name; no chat generation request was sent.",
    }



_SETTINGS_LOCK = threading.RLock()


def _load_settings_file(path: Path) -> dict[str, Any] | None:
    """Read a valid settings object, or None if the file is absent/corrupt."""
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    return {key: value for key, value in loaded.items() if key in DEFAULTS}


def load_settings() -> dict[str, Any]:
    """Load current settings, recovering from the backup if the primary is unreadable."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with _SETTINGS_LOCK:
        loaded = _load_settings_file(SETTINGS_FILE)
        if loaded is None:
            loaded = _load_settings_file(SETTINGS_FILE.with_suffix(SETTINGS_FILE.suffix + ".bak"))
        data = DEFAULTS.copy()
        if loaded is not None:
            data.update(loaded)
        return data


def save_settings(data: dict[str, Any]) -> None:
    """Atomically persist the allow-listed settings and refresh a local recovery copy."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    safe = {key: data.get(key, DEFAULTS[key]) for key in DEFAULTS}
    payload = json.dumps(safe, ensure_ascii=False, indent=2) + "\n"
    with _SETTINGS_LOCK:
        _atomic_write_text(SETTINGS_FILE, payload)
        # Backup failure must not report the already-committed primary save as failed.
        try:
            _atomic_write_text(SETTINGS_FILE.with_suffix(SETTINGS_FILE.suffix + ".bak"), payload)
        except OSError:
            pass


def _atomic_write_text(destination: Path, payload: str) -> None:
    """Flush a unique same-directory temporary file before atomic replacement."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(destination)
        _fsync_parent_directory(destination.parent)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _fsync_parent_directory(directory: Path) -> None:
    """Best-effort directory metadata sync; not all Windows filesystems support it."""
    try:
        descriptor = os.open(str(directory), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


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
