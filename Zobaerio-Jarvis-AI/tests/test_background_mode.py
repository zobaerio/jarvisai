from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BackgroundModeTests(unittest.TestCase):
    def test_close_dialog_offers_background_exit_and_cancel_choices(self) -> None:
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("messagebox.askyesnocancel(", source)
        self.assertIn("keep J.A.R.V.I.S running in the system tray", source)
        self.assertIn("self._enter_background_mode()", source)
        self.assertIn("self._exit_application()", source)

    def test_background_mode_hides_without_cancelling_active_task(self) -> None:
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        start = source.index("    def _enter_background_mode(self) -> None:")
        end = source.index("    def _restore_from_tray(self) -> None:", start)
        background_method = source[start:end]
        self.assertIn("self.root.withdraw()", background_method)
        self.assertIn("self._tray_icon.run", background_method)
        self.assertNotIn("_active_task_cancel_event.set()", background_method)
        self.assertIn("self._write_message", background_method)

    def test_tray_can_restore_and_exit_with_active_task_warning(self) -> None:
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("def _restore_from_tray(self) -> None:", source)
        self.assertIn("self.root.deiconify()", source)
        self.assertIn("def _exit_from_tray(self) -> None:", source)
        self.assertIn('"Exit while a task is running?"', source)
        self.assertIn("self._tray_icon.stop()", source)

    def test_pystray_is_installed_and_bundled(self) -> None:
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        spec = (ROOT / "JARVIS.spec").read_text(encoding="utf-8")
        self.assertIn("pystray>=0.19.5", requirements)
        self.assertIn('"pystray._win32"', spec)


if __name__ == "__main__":
    unittest.main()
