"""Persistent, bounded task history for the J.A.R.V.I.S desktop assistant."""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .settings import APP_DIR
from .version import APP_VERSION

DEFAULT_HISTORY_FILE = APP_DIR / "task_history.json"
MAX_TASKS = 100
MAX_STEPS = 40
MAX_COMMAND_LENGTH = 600
MAX_RESULT_LENGTH = 6000
MAX_ACTIONS_PER_TASK = 16

TASK_HISTORY_STATUSES = (
    "all",
    "queued",
    "running",
    "cancelling",
    "completed",
    "partial",
    "failed",
    "cancelled",
)


def _parse_diagnostic_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_safe_diagnostics(
    records: list[dict[str, Any]],
    *,
    app_version: str = APP_VERSION,
    os_name: str = "unknown",
    python_version: str = "unknown",
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a shareable aggregate report without user commands or content-bearing fields."""
    rows = [record for record in records if isinstance(record, dict)][:MAX_TASKS]
    status_counts = {status: 0 for status in TASK_HISTORY_STATUSES if status != "all"}
    status_counts["unknown"] = 0
    action_status_counts: dict[str, int] = {
        "running": 0,
        "result_received": 0,
        "failed": 0,
        "interrupted": 0,
        "unknown": 0,
    }
    task_summaries: list[dict[str, Any]] = []
    progress_total = 0
    action_total = 0

    for ordinal, record in enumerate(rows, start=1):
        raw_status = str(record.get("status", "unknown")).strip().lower()
        status = raw_status if raw_status in status_counts else "unknown"
        status_counts[status] += 1
        steps = record.get("steps")
        actions = record.get("actions")
        valid_steps = [step for step in steps if isinstance(step, dict)] if isinstance(steps, list) else []
        valid_actions = [action for action in actions if isinstance(action, dict)] if isinstance(actions, list) else []
        progress_count = min(len(valid_steps), MAX_STEPS)
        action_count = min(len(valid_actions), MAX_ACTIONS_PER_TASK)
        progress_total += progress_count
        action_total += action_count

        per_task_action_statuses = {"running": 0, "result_received": 0, "failed": 0, "interrupted": 0, "unknown": 0}
        for action in valid_actions[:MAX_ACTIONS_PER_TASK]:
            action_status = str(action.get("status", "unknown")).strip().lower()
            if action_status not in per_task_action_statuses:
                action_status = "unknown"
            per_task_action_statuses[action_status] += 1
            action_status_counts[action_status] += 1

        created = _parse_diagnostic_timestamp(record.get("created_at"))
        finished = _parse_diagnostic_timestamp(record.get("finished_at"))
        elapsed: float | None = None
        if created is not None and finished is not None and finished >= created:
            elapsed = round((finished - created).total_seconds(), 2)

        task_summaries.append({
            "task_number": ordinal,
            "status": status,
            "created_date_utc": created.date().isoformat() if created is not None else None,
            "duration_seconds": elapsed,
            "progress_event_count": progress_count,
            "tool_action_count": action_count,
            "tool_action_status_counts": per_task_action_statuses,
        })

    return {
        "schema_version": 1,
        "generated_at_utc": generated_at or datetime.now(timezone.utc).isoformat(),
        "app_version": str(app_version)[:32],
        "runtime": {
            "operating_system_family": str(os_name)[:40],
            "python_version": str(python_version)[:40],
        },
        "summary": {
            "task_count": len(rows),
            "status_counts": status_counts,
            "progress_event_count": progress_total,
            "tool_action_count": action_total,
            "tool_action_status_counts": action_status_counts,
        },
        "tasks": task_summaries,
        "privacy": {
            "excluded": [
                "task IDs",
                "commands and prompts",
                "task result text",
                "file paths and file names",
                "progress text",
                "tool names and arguments",
                "tool result payloads",
                "exception details",
            ],
            "note": "Aggregate execution metadata only; no user task text or tool payloads are exported.",
        },
    }


def filter_task_records(
    records: list[dict[str, Any]],
    *,
    query: str = "",
    status: str = "all",
) -> list[dict[str, Any]]:
    """Filter an already bounded history snapshot without mutating or persisting it."""
    normalized_status = str(status or "all").strip().lower()
    if normalized_status not in TASK_HISTORY_STATUSES:
        raise ValueError("Unsupported task-history status filter")
    needle = " ".join(str(query or "").split())[:300].casefold()
    filtered: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        record_status = str(record.get("status", "unknown")).casefold()
        if normalized_status != "all" and record_status != normalized_status:
            continue
        if needle:
            parts = [
                str(record.get("id", "")),
                str(record.get("command", "")),
                str(record.get("result", "")),
                record_status,
            ]
            steps = record.get("steps")
            if isinstance(steps, list):
                parts.extend(
                    str(step.get("text", ""))
                    for step in steps
                    if isinstance(step, dict)
                )
            actions = record.get("actions")
            if isinstance(actions, list):
                for action in actions:
                    if isinstance(action, dict):
                        parts.extend([
                            str(action.get("name", "")),
                            str(action.get("status", "")),
                            str(action.get("note", "")),
                        ])
            if needle not in " ".join(parts).casefold():
                continue
        filtered.append(record)
    return filtered


_PATH_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, Any] = {}


def _lock_for_path(path: Path) -> threading.RLock:
    """Share one in-process lock between TaskStore objects that use the same file."""
    key = os.path.normcase(str(path.resolve()))
    with _PATH_LOCKS_GUARD:
        lock = _PATH_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _PATH_LOCKS[key] = lock
        return lock



def _process_is_running(pid: int) -> bool:
    """Conservatively check whether an owner process may still be alive."""
    if type(pid) is not int or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = [
                wintypes.DWORD, wintypes.BOOL, wintypes.DWORD
            ]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            process_query_limited_information = 0x1000
            handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            # Access denied means a process likely exists; do not risk recovering it as stale.
            return ctypes.get_last_error() == 5
        except Exception:
            # Unknown Windows API errors must not cause an active task to be marked stale.
            return True
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except OverflowError:
        return False
    except PermissionError:
        return True
    except OSError:
        # If the process status cannot be established, leave the task for manual review.
        return True


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class TaskStore:
    """Small atomic JSON task store. No command content is sent off-device by this module."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else DEFAULT_HISTORY_FILE
        self._lock = _lock_for_path(self.path)

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

    def create_task(self, command: str, *, status: str = "running") -> dict[str, Any]:
        if status not in {"queued", "running"}:
            raise ValueError("New tasks can only be queued or started.")
        now = _now()
        row: dict[str, Any] = {
            "id": uuid.uuid4().hex[:12],
            "command": str(command).strip()[:MAX_COMMAND_LENGTH],
            "status": status,
            "created_at": now,
            "updated_at": now,
            "finished_at": None,
            "result": "",
            "steps": [],
            "actions": [],
            "process_id": os.getpid(),
        }
        with self._lock:
            rows = self._read()
            rows.append(row)
            self._write(rows[-MAX_TASKS:])
        return dict(row)

    def next_queued_task(self) -> dict[str, Any] | None:
        """Return the oldest queued task without changing its state."""
        with self._lock:
            for row in self._read():
                if row.get("status") == "queued":
                    return dict(row)
        return None

    def queued_count(self) -> int:
        with self._lock:
            return sum(1 for row in self._read() if row.get("status") == "queued")

    def update_task(
        self,
        task_id: str,
        *,
        status: str | None = None,
        result: str | None = None,
        step: str | None = None,
    ) -> dict[str, Any] | None:
        allowed_statuses = {"queued", "running", "cancelling", "completed", "partial", "failed", "cancelled"}
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
                if status == "running":
                    target["process_id"] = os.getpid()
                if status in {"completed", "partial", "failed", "cancelled"}:
                    target["finished_at"] = now
            if result is not None:
                target["result"] = str(result)[:MAX_RESULT_LENGTH]
            if step:
                steps = target.setdefault("steps", [])
                steps.append({"time": now, "text": " ".join(str(step).split())[:240]})
                target["steps"] = steps[-MAX_STEPS:]
            self._write(rows[-MAX_TASKS:])
            return dict(target)


    def set_task_plan(self, task_id: str, step_titles: list[str]) -> dict[str, Any] | None:
        """Persist a bounded, resumable plan without executing or auto-replaying any step."""
        if not isinstance(step_titles, list) or not step_titles or len(step_titles) > MAX_STEPS:
            raise ValueError(f"A task plan must contain 1 to {MAX_STEPS} steps.")
        titles: list[str] = []
        for title in step_titles:
            if not isinstance(title, str):
                raise ValueError("Every task-plan step must be text.")
            normalized = " ".join(title.split())
            if not normalized or len(normalized) > 240:
                raise ValueError("Task-plan steps must contain 1 to 240 characters.")
            titles.append(normalized)

        with self._lock:
            rows = self._read()
            target = next((row for row in rows if row.get("id") == task_id), None)
            if target is None or target.get("status") not in {"queued", "running"}:
                return None
            now = _now()
            target["plan"] = [
                {
                    "id": uuid.uuid4().hex[:12],
                    "title": title,
                    "status": "pending",
                    "attempts": 0,
                    "created_at": now,
                    "updated_at": now,
                }
                for title in titles
            ]
            target["updated_at"] = now
            self._write(rows[-MAX_TASKS:])
            return dict(target)

    def update_plan_step(
        self, task_id: str, step_id: str, *, status: str
    ) -> dict[str, Any] | None:
        """Persist one step transition; retrying a failed step is always explicit."""
        if status not in {"pending", "running", "completed", "failed", "skipped", "unverified"}:
            raise ValueError(f"Unsupported plan-step status: {status}")
        allowed_transitions = {
            "pending": {"running", "skipped"},
            "running": {"completed", "failed"},
            "failed": {"pending"},
            "completed": set(),
            "skipped": set(),
            "unverified": set(),
        }
        with self._lock:
            rows = self._read()
            target = next((row for row in rows if row.get("id") == task_id), None)
            if target is None or target.get("status") not in {"queued", "running"}:
                return None
            plan = target.get("plan")
            if not isinstance(plan, list):
                return None
            item = next(
                (step for step in plan if isinstance(step, dict) and step.get("id") == step_id),
                None,
            )
            if item is None:
                return None
            current = item.get("status")
            if status not in allowed_transitions.get(current, set()):
                raise ValueError(f"Invalid plan-step transition: {current} -> {status}")
            now = _now()
            item["status"] = status
            item["updated_at"] = now
            if status == "running":
                attempts = item.get("attempts", 0)
                if type(attempts) is not int or attempts < 0:
                    attempts = 0
                item["attempts"] = min(999, attempts + 1)
            target["updated_at"] = now
            self._write(rows[-MAX_TASKS:])
            return dict(target)

    def finalize_task_plan(self, task_id: str, outcome: str) -> dict[str, Any] | None:
        """Mark untouched plan items unverified when the task ends; never infer completion."""
        if outcome not in {"completed", "partial", "failed", "cancelled"}:
            raise ValueError(f"Unsupported task outcome: {outcome}")
        with self._lock:
            rows = self._read()
            target = next((row for row in rows if row.get("id") == task_id), None)
            if target is None:
                return None
            plan = target.get("plan")
            if not isinstance(plan, list):
                return dict(target)
            now = _now()
            changed = False
            for item in plan:
                if not isinstance(item, dict) or item.get("status") not in {"pending", "running"}:
                    continue
                item["status"] = "unverified"
                item["updated_at"] = now
                item["outcome"] = outcome
                item["verification_note"] = "Task ended without a dedicated execution/verification event for this plan step."
                changed = True
            if changed:
                target["updated_at"] = now
                self._write(rows[-MAX_TASKS:])
            return dict(target)

    def cancel_queued_task(self, task_id: str) -> dict[str, Any] | None:
        """Cancel a queued command without executing it; active or terminal tasks are untouched."""
        with self._lock:
            rows = self._read()
            target = next((row for row in rows if row.get("id") == task_id), None)
            if target is None or target.get("status") != "queued":
                return None
            now = _now()
            target["status"] = "cancelled"
            target["updated_at"] = now
            target["finished_at"] = now
            target["result"] = "Queued command cancelled before execution. It was not run."
            steps = target.get("steps")
            if not isinstance(steps, list):
                steps = []
            steps.append({
                "time": now,
                "text": "Queued command cancelled by user before execution",
            })
            target["steps"] = steps[-MAX_STEPS:]
            self._write(rows[-MAX_TASKS:])
            return dict(target)

    def start_action(self, task_id: str, name: str) -> str | None:
        """Record a tool start without persisting its arguments or returned content."""
        safe_name = " ".join(str(name).split())[:80] or "unknown"
        action_id = uuid.uuid4().hex[:12]
        with self._lock:
            rows = self._read()
            target = next((row for row in rows if row.get("id") == task_id), None)
            if target is None:
                return None
            now = _now()
            actions = target.get("actions")
            if not isinstance(actions, list):
                actions = []
            actions.append({
                "id": action_id,
                "name": safe_name,
                "status": "running",
                "started_at": now,
                "finished_at": None,
                "note": "",
            })
            target["actions"] = actions[-MAX_ACTIONS_PER_TASK:]
            target["updated_at"] = now
            self._write(rows[-MAX_TASKS:])
            return action_id

    def finish_action(
        self,
        task_id: str,
        action_id: str,
        *,
        status: str,
        note: str = "",
    ) -> dict[str, Any] | None:
        """Finish a running action with a bounded, non-content-bearing diagnostic note."""
        if status not in {"result_received", "failed"}:
            raise ValueError(f"Unsupported action status: {status}")
        safe_note = " ".join(str(note).split())[:120]
        with self._lock:
            rows = self._read()
            target = next((row for row in rows if row.get("id") == task_id), None)
            if target is None:
                return None
            actions = target.get("actions")
            if not isinstance(actions, list):
                return None
            action = next(
                (
                    item for item in reversed(actions)
                    if isinstance(item, dict)
                    and item.get("id") == action_id
                    and item.get("status") == "running"
                ),
                None,
            )
            if action is None:
                return None
            now = _now()
            action["status"] = status
            action["finished_at"] = now
            action["note"] = safe_note
            target["updated_at"] = now
            self._write(rows[-MAX_TASKS:])
            return dict(action)

    def recover_interrupted_tasks(self) -> int:
        """Mark abandoned active tasks failed without automatically replaying risky actions."""
        recovery_note = (
            "Interrupted by an app restart. This task may have partially completed, so it was not "
            "automatically rerun to avoid duplicating actions. Review Task History before retrying."
        )
        recovery_step = "Startup recovery: previous execution was interrupted; task marked failed and not auto-replayed"
        with self._lock:
            rows = self._read()
            now = _now()
            recovered = 0
            for row in rows:
                if row.get("status") not in {"running", "cancelling"}:
                    continue
                owner_pid = row.get("process_id")
                # If another J.A.R.V.I.S process still appears active, leave its task alone.
                # Legacy rows without a PID are treated as interrupted by the newer app.
                if type(owner_pid) is int and _process_is_running(owner_pid):
                    continue
                previous_result = str(row.get("result", "")).strip()
                combined_result = (
                    previous_result + "\n\n" + recovery_note if previous_result else recovery_note
                )
                row["status"] = "failed"
                row["updated_at"] = now
                row["finished_at"] = now
                row["result"] = combined_result[:MAX_RESULT_LENGTH]
                steps = row.get("steps")
                if not isinstance(steps, list):
                    steps = []
                steps.append({"time": now, "text": recovery_step[:240]})
                row["steps"] = steps[-MAX_STEPS:]
                actions = row.get("actions")
                if not isinstance(actions, list):
                    actions = []
                for action in actions[-MAX_ACTIONS_PER_TASK:]:
                    if isinstance(action, dict) and action.get("status") == "running":
                        action["status"] = "interrupted"
                        action["finished_at"] = now
                        action["note"] = (
                            "App restarted while this action was in progress; outcome is unknown. "
                            "It was not replayed."
                        )
                row["actions"] = actions[-MAX_ACTIONS_PER_TASK:]
                recovered += 1
            if recovered:
                self._write(rows[-MAX_TASKS:])
            return recovered

    @property
    def backup_path(self) -> Path:
        return self.path.with_suffix(self.path.suffix + ".bak")

    @staticmethod
    def _load_rows(path: Path) -> list[dict[str, Any]] | None:
        """Return valid bounded records, or None when the JSON file is absent/corrupt."""
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, list):
            return None
        rows: list[dict[str, Any]] = []
        for item in raw[-MAX_TASKS:]:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                rows.append(item)
        return rows

    def _read(self) -> list[dict[str, Any]]:
        primary = self._load_rows(self.path)
        if primary is not None:
            return primary
        # A valid backup is preferred to silently losing all task history when
        # the primary JSON is truncated or damaged by an interrupted write.
        backup = self._load_rows(self.backup_path)
        return backup if backup is not None else []

    def _write(self, rows: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(rows[-MAX_TASKS:], ensure_ascii=False, indent=2) + "\n"
        self._atomic_write_text(self.path, payload)
        # Back up the committed primary after the atomic replacement. Backup
        # failures must not turn a successful primary save into a failed task update.
        try:
            self._atomic_write_text(self.backup_path, payload)
        except OSError:
            pass

    def _atomic_write_text(self, destination: Path, payload: str) -> None:
        """Flush a uniquely named same-directory temporary file before atomic replace."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            temp.replace(destination)
            self._fsync_parent_directory(destination.parent)
        finally:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _fsync_parent_directory(directory: Path) -> None:
        """Best-effort directory metadata sync (not supported by every Windows filesystem)."""
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
