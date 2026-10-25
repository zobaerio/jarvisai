"""Persistent, bounded task history for the J.A.R.V.I.S desktop assistant."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .settings import APP_DIR

DEFAULT_HISTORY_FILE = APP_DIR / "task_history.json"
MAX_TASKS = 100
MAX_STEPS = 40
MAX_COMMAND_LENGTH = 600
MAX_RESULT_LENGTH = 6000


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class TaskStore:
    """Small atomic JSON task store. No command content is sent off-device by this module."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else DEFAULT_HISTORY_FILE
        self._lock = threading.RLock()

    def list_tasks(self, limit: int = MAX_TASKS) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._read()
            safe_limit = max(0, min(int(limit), MAX_TASKS))
            return [dict(row) for row in reversed(rows[-safe_limit:])] if safe_limit else []

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            for row in reversed(self._read()):
                if row.get("id") == task_id:
                    return dict(row)
        return None

    def create_task(self, command: str) -> dict[str, Any]:
        now = _now()
        row: dict[str, Any] = {
            "id": uuid.uuid4().hex[:12],
            "command": str(command).strip()[:MAX_COMMAND_LENGTH],
            "status": "running",
            "created_at": now,
            "updated_at": now,
            "finished_at": None,
            "result": "",
            "steps": [],
        }
        with self._lock:
            rows = self._read()
            rows.append(row)
            self._write(rows[-MAX_TASKS:])
        return dict(row)

    def update_task(
        self,
        task_id: str,
        *,
        status: str | None = None,
        result: str | None = None,
        step: str | None = None,
    ) -> dict[str, Any] | None:
        allowed_statuses = {"queued", "running", "cancelling", "completed", "failed", "cancelled"}
        if status is not None and status not in allowed_statuses:
            raise ValueError(f"Unsupported task status: {status}")
        with self._lock:
            rows = self._read()
            target = next((row for row in rows if row.get("id") == task_id), None)
            if target is None:
                return None
            now = _now()
            target["updated_at"] = now
            if status is not None:
                target["status"] = status
                if status in {"completed", "failed", "cancelled"}:
                    target["finished_at"] = now
            if result is not None:
                target["result"] = str(result)[:MAX_RESULT_LENGTH]
            if step:
                steps = target.setdefault("steps", [])
                steps.append({"time": now, "text": " ".join(str(step).split())[:240]})
                target["steps"] = steps[-MAX_STEPS:]
            self._write(rows[-MAX_TASKS:])
            return dict(target)

    def _read(self) -> list[dict[str, Any]]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(raw, list):
            return []
        rows: list[dict[str, Any]] = []
        for item in raw[-MAX_TASKS:]:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                rows.append(item)
        return rows

    def _write(self, rows: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)
