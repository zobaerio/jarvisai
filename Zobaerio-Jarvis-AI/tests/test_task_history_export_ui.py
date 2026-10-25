from __future__ import annotations

import unittest
from pathlib import Path


APP_SOURCE = Path(__file__).resolve().parents[1] / "app.py"


class SelectedTaskExportUiTests(unittest.TestCase):
    def test_export_button_is_separate_from_safe_diagnostics(self) -> None:
        source = APP_SOURCE.read_text(encoding="utf-8")
        self.assertIn('text="Export Selected Task", command=export_selected_task', source)
        self.assertIn('text="Export Safe Diagnostics", command=export_safe_diagnostics', source)

    def test_detailed_export_warns_about_sensitive_content_before_saving(self) -> None:
        source = APP_SOURCE.read_text(encoding="utf-8")
        warning = source.index('"Export the full selected task record as JSON?')
        save_dialog = source.index("filedialog.asksaveasfilename(", warning)
        self.assertLess(warning, save_dialog)
        self.assertIn("Unlike Safe Diagnostics, this file can contain the command, result, progress text", source)
        self.assertIn("Review it for private command text or file paths before sharing.", source)

    def test_export_handles_no_selection_and_existing_file(self) -> None:
        source = APP_SOURCE.read_text(encoding="utf-8")
        self.assertIn('messagebox.showinfo("Export task", "Select a task from the history list first."', source)
        self.assertIn('"Overwrite task export?"', source)
        self.assertIn('json.dumps(record, indent=2, ensure_ascii=False)', source)


if __name__ == "__main__":
    unittest.main()
