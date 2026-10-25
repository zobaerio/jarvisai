"""Opt-in per-user Windows login startup registration for J.A.R.V.I.S."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "Zobaerio.JARVIS"


def build_startup_command(
    *,
    executable: str | None = None,
    app_script: str | None = None,
    frozen: bool | None = None,
) -> str:
    """Build a correctly quoted command for packaged or source-based startup."""
    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else bool(frozen)
    exe = str(executable or sys.executable)
    if is_frozen:
        return subprocess.list2cmdline([exe])
    script = str(app_script or (Path(__file__).resolve().parents[1] / "app.py"))
    pythonw = Path(exe)
    if pythonw.name.casefold() == "python.exe":
        pythonw = pythonw.with_name("pythonw.exe")
    return subprocess.list2cmdline([str(pythonw), script])


def is_windows_startup_enabled(*, winreg_module: Any = None, is_windows: bool | None = None) -> bool:
    """Return whether this app's per-user Run entry exists; never changes OS settings."""
    supported = os.name == "nt" if is_windows is None else bool(is_windows)
    if not supported:
        return False
    if winreg_module is None:
        import winreg as winreg_module  # type: ignore[import-not-found]
    try:
        with winreg_module.OpenKey(
            winreg_module.HKEY_CURRENT_USER, RUN_KEY, 0, winreg_module.KEY_QUERY_VALUE
        ) as key:
            value, _kind = winreg_module.QueryValueEx(key, RUN_VALUE_NAME)
        return isinstance(value, str) and bool(value.strip())
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_windows_startup(
    enabled: bool,
    *,
    winreg_module: Any = None,
    is_windows: bool | None = None,
    executable: str | None = None,
    app_script: str | None = None,
    frozen: bool | None = None,
) -> bool:
    """Enable or disable startup for the current Windows user only.

    This touches only this application's named HKCU Run value. It never requests
    administrator rights and never edits machine-wide startup configuration.
    """
    supported = os.name == "nt" if is_windows is None else bool(is_windows)
    if not supported:
        if enabled:
            raise OSError("Automatic login startup is supported only on Windows.")
        return False
    if winreg_module is None:
        import winreg as winreg_module  # type: ignore[import-not-found]
    access = winreg_module.KEY_SET_VALUE | winreg_module.KEY_QUERY_VALUE
    try:
        key = winreg_module.CreateKeyEx(
            winreg_module.HKEY_CURRENT_USER, RUN_KEY, 0, access
        )
        with key:
            if enabled:
                command = build_startup_command(
                    executable=executable, app_script=app_script, frozen=frozen
                )
                winreg_module.SetValueEx(
                    key, RUN_VALUE_NAME, 0, winreg_module.REG_SZ, command
                )
            else:
                try:
                    winreg_module.DeleteValue(key, RUN_VALUE_NAME)
                except FileNotFoundError:
                    pass
    except OSError:
        raise
    return bool(enabled)
