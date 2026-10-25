"""Local-only preflight checks for the J.A.R.V.I.S desktop runtime."""
from __future__ import annotations

import importlib.util
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any


@dataclass(frozen=True)
class HealthCheck:
    component: str
    status: str
    detail: str


def _runtime_root() -> Path:
    """Resolve assets from source checkout or a PyInstaller one-folder build."""
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(str(bundled_root))
    return Path(__file__).resolve().parent.parent


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError, AttributeError):
        return False


def collect_system_health(
    settings: dict[str, Any],
    *,
    project_root: str | Path | None = None,
    python_version: tuple[int, int, int] | None = None,
    os_name: str | None = None,
    frozen: bool | None = None,
    module_available: Callable[[str], bool] | None = None,
    local_endpoint: Callable[[str], bool] | None = None,
    api_key_resolver: Callable[[dict[str, Any]], str | None] | None = None,
) -> list[HealthCheck]:
    """Return fast, local preflight checks without contacting endpoints or revealing secrets.

    The check does not open the microphone, test speakers, send an AI request, or inspect
    user files. It validates configuration presence and local runtime prerequisites only.
    """
    root = Path(project_root) if project_root is not None else _runtime_root()
    active_python = python_version or sys.version_info[:3]
    active_os = os_name or platform.system()
    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    has_module = module_available or _module_available
    checks: list[HealthCheck] = []

    if active_python[:2] == (3, 12):
        checks.append(HealthCheck("Python runtime", "PASS", f"Python {active_python[0]}.{active_python[1]} detected."))
    else:
        checks.append(HealthCheck("Python runtime", "WARN", "Python 3.12 is the supported packaging target; verify dependency compatibility."))

    if active_os == "Windows":
        checks.append(HealthCheck("Desktop platform", "PASS", "Windows desktop environment detected."))
    else:
        checks.append(HealthCheck("Desktop platform", "WARN", "Some desktop automation features require Windows."))

    if (root / "assets" / "avatar_studio.html").is_file():
        checks.append(HealthCheck("3D Character Studio", "PASS", "The local 3D Studio page is present."))
    else:
        checks.append(HealthCheck("3D Character Studio", "FAIL", "The 3D Studio page is missing from the app package."))

    if (root / "assets" / "branding" / "jarvis-mark.svg").is_file():
        checks.append(HealthCheck("Branding assets", "PASS", "The app logo asset is present."))
    else:
        checks.append(HealthCheck("Branding assets", "WARN", "A source logo asset was not found; runtime-generated branding may still be available."))

    if is_frozen:
        checks.append(HealthCheck("Package mode", "PASS", "Running as a packaged application."))
    else:
        checks.append(HealthCheck("Package mode", "PASS", "Running from the Python source environment."))

    missing_core = [name for name in ("requests", "PIL") if not has_module(name)]
    if not missing_core:
        checks.append(HealthCheck("Core dependencies", "PASS", "HTTP client and image library are available."))
    else:
        checks.append(HealthCheck("Core dependencies", "FAIL", "Missing required runtime module(s): " + ", ".join(missing_core)))

    missing_desktop = [name for name in ("psutil", "pyautogui", "pyperclip") if not has_module(name)]
    if not missing_desktop:
        checks.append(HealthCheck("Desktop automation", "PASS", "System information and approved foreground actions have their dependencies."))
    else:
        checks.append(HealthCheck("Desktop automation", "WARN", "Some desktop actions may be unavailable; missing module(s): " + ", ".join(missing_desktop)))

    speech_modules = ("speech_recognition", "pyaudio", "edge_tts", "pyttsx3", "pygame")
    missing_speech = [name for name in speech_modules if not has_module(name)]
    if not missing_speech:
        checks.append(HealthCheck("Speech features", "PASS", "Speech-related Python packages are installed. Hardware was not tested."))
    else:
        checks.append(HealthCheck("Speech features", "WARN", "Speech features may be limited; missing module(s): " + ", ".join(missing_speech)))

    endpoint = str(settings.get("api_base_url", "") or "").strip()
    model = str(settings.get("model", "") or "").strip()
    if not endpoint or not model:
        checks.append(HealthCheck("AI model configuration", "WARN", "Configure the AI endpoint and model in Settings before using model-powered tasks."))
    else:
        checks.append(HealthCheck("AI model configuration", "PASS", "An endpoint and model are configured; network reachability was not tested."))
        local_check = local_endpoint
        key_resolver = api_key_resolver
        try:
            if local_check is None or key_resolver is None:
                from .settings import get_api_key, is_local_api_endpoint
                local_check = local_check or is_local_api_endpoint
                key_resolver = key_resolver or get_api_key
            is_local = bool(local_check(endpoint))
        except Exception:
            # Do not surface provider URLs, keyring errors, or configuration exception text.
            is_local = False
        if is_local:
            checks.append(HealthCheck("AI API key", "PASS", "A local endpoint is configured; an API key is optional."))
        else:
            try:
                key_present = bool(key_resolver(settings)) if key_resolver is not None else False
            except Exception:
                key_present = False
            if key_present:
                checks.append(HealthCheck("AI API key", "PASS", "A cloud API key is available; its value is never displayed. Connection was not tested."))
            else:
                checks.append(HealthCheck("AI API key", "WARN", "A cloud endpoint/model is configured, but a key was not found or secure storage could not verify it."))

    return checks


def summarize_system_health(checks: list[HealthCheck]) -> dict[str, int | str]:
    """Summarize statuses without including environment-specific paths or configuration."""
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for check in checks:
        counts[check.status if check.status in counts else "WARN"] += 1
    overall = "FAIL" if counts["FAIL"] else "WARN" if counts["WARN"] else "PASS"
    return {"overall": overall, **counts}
