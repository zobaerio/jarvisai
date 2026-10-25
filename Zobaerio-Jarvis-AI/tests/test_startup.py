from __future__ import annotations

import unittest
from pathlib import Path

from jarvis.startup import (
    RUN_KEY,
    RUN_VALUE_NAME,
    build_startup_command,
    is_windows_startup_enabled,
    set_windows_startup,
)


class FakeKey:
    def __init__(self, store: dict[str, str]) -> None:
        self.store = store
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False


class FakeWinreg:
    HKEY_CURRENT_USER = object()
    KEY_QUERY_VALUE = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
    def OpenKey(self, _root, path, _reserved, _access):
        if path != RUN_KEY:
            raise AssertionError("Unexpected registry path")
        if not self.values:
            raise FileNotFoundError()
        return FakeKey(self.values)
    def CreateKeyEx(self, _root, path, _reserved, _access):
        if path != RUN_KEY:
            raise AssertionError("Unexpected registry path")
        return FakeKey(self.values)
    def QueryValueEx(self, _key, name):
        if name not in self.values:
            raise FileNotFoundError()
        return self.values[name], self.REG_SZ
    def SetValueEx(self, key, name, _reserved, _kind, value):
        key.store[name] = value
    def DeleteValue(self, key, name):
        if name not in key.store:
            raise FileNotFoundError()
        del key.store[name]


class WindowsStartupTests(unittest.TestCase):
    def test_packaged_command_is_quoted(self) -> None:
        command = build_startup_command(executable=r"C:\Program Files\JARVIS\JARVIS.exe", frozen=True)
        self.assertEqual(command, '"C:\\Program Files\\JARVIS\\JARVIS.exe"')

    def test_source_command_uses_pythonw_and_script(self) -> None:
        command = build_startup_command(
            executable=r"C:\Python312\python.exe",
            app_script=r"C:\Users\User Name\JARVIS\app.py",
            frozen=False,
        )
        self.assertIn("pythonw.exe", command)
        self.assertIn('"C:\\Users\\User Name\\JARVIS\\app.py"', command)

    def test_startup_is_opt_in_and_removable(self) -> None:
        registry = FakeWinreg()
        self.assertFalse(is_windows_startup_enabled(winreg_module=registry, is_windows=True))
        self.assertTrue(set_windows_startup(True, winreg_module=registry, is_windows=True, executable=r"C:\JARVIS.exe", frozen=True))
        self.assertTrue(is_windows_startup_enabled(winreg_module=registry, is_windows=True))
        self.assertTrue(registry.values[RUN_VALUE_NAME].endswith("JARVIS.exe"))
        self.assertFalse(set_windows_startup(False, winreg_module=registry, is_windows=True))
        self.assertFalse(is_windows_startup_enabled(winreg_module=registry, is_windows=True))

    def test_non_windows_does_not_modify_startup(self) -> None:
        registry = FakeWinreg()
        self.assertFalse(set_windows_startup(False, winreg_module=registry, is_windows=False))
        with self.assertRaises(OSError):
            set_windows_startup(True, winreg_module=registry, is_windows=False)
        self.assertEqual(registry.values, {})


if __name__ == "__main__":
    unittest.main()
