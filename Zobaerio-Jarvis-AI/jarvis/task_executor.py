"""Safe step-by-step execution of persisted J.A.R.V.I.S task plans.

The executor never replays a task automatically after restart. A plan step is only
marked completed when it returned a text deliverable, a read-only tool result, or a
positive deterministic local verification. A state-changing tool result without
verification stops the plan and leaves that step explicitly unverified.
"""
from __future__ import annotations

import threading
from typing import Any, Callable

from .agent import MAX_TOOL_CALLS_PER_TASK, READ_ONLY_TOOL_NAMES
from .task_planner import format_plan_step_guidance
from .task_store import TaskStore

ProgressCallback = Callable[[str], None]
ToolCallback = Callable[[str, str, str | None, str], str | None]
ToolCallbackFactory = Callable[[str], ToolCallback]

MAX_PLAN_RESULT_CHARS = 6000
MAX_STEP_RESULT_CHARS = 900


def execute_task_plan(
    *,
    agent: Any,
    task_store: TaskStore,
    task_id: str,
    user_text: str,
    cancel_event: threading.Event,
    progress: ProgressCallback | None = None,
    tool_event_factory: ToolCallbackFactory | None = None,
) -> tuple[str, str]:
    """Execute each persisted step in order under one shared tool-action budget."""
    record = task_store.get_task(task_id)
    if not isinstance(record, dict):
        return "The stored task could not be reloaded. No plan steps were started.", "failed"
    raw_plan = record.get("plan")
    if not isinstance(raw_plan, list) or not raw_plan:
        return "No persisted task plan is available to execute.", "failed"

    plan_steps = [
        item for item in raw_plan
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("title"), str)
    ]
    if not plan_steps or len(plan_steps) != len(raw_plan):
        return "The stored task plan is malformed. No plan steps were started.", "failed"

    titles = [" ".join(str(item["title"]).split())[:180] for item in plan_steps]
    if any(not title for title in titles):
        return "The stored task plan contains an empty step. No plan steps were started.", "failed"

    outputs: list[str] = []
    completed_count = 0
    total_tool_calls = 0
    final_status = "completed"
    stop_reason = ""

    def report(message: str) -> None:
        if progress is None:
            return
        try:
            progress(message)
        except Exception:
            # UI/history telemetry must not break execution.
            pass

    for index, item in enumerate(plan_steps):
        if cancel_event.is_set():
            final_status = "cancelled"
            stop_reason = "Task cancellation was received; remaining steps were not started."
            break

        remaining_budget = MAX_TOOL_CALLS_PER_TASK - total_tool_calls
        if remaining_budget <= 0:
            final_status = "partial"
            stop_reason = (
                f"The shared safety limit of {MAX_TOOL_CALLS_PER_TASK} tool actions was reached. "
                "Remaining steps were not started."
            )
            report("Task-plan action budget exhausted; remaining steps will not start")
            break

        step_id = str(item["id"])
        title = titles[index]
        updated = task_store.update_plan_step(task_id, step_id, status="running")
        if updated is None:
            final_status = "partial" if completed_count else "failed"
            stop_reason = "A plan step could not be moved into the running state; execution stopped."
            break

        report(f"Executing plan step {index + 1}/{len(plan_steps)}: {title}")
        tool_event = tool_event_factory(step_id) if tool_event_factory else None
        try:
            answer = agent.respond(
                format_plan_step_guidance(user_text, titles, index),
                cancel_event=cancel_event,
                progress=progress,
                tool_event=tool_event,
                tool_budget=remaining_budget,
            )
        except Exception:
            # Keep exception text out of the step record and user-facing result.
            answer = "This plan step could not be completed because an internal worker error occurred."
            try:
                agent.last_outcome = "failed"
                agent.last_tool_call_count = 0
                agent.last_tool_call_names = []
                agent.last_tool_call_failures = 1
                agent.last_verification_succeeded = False
            except Exception:
                pass

        raw_count = getattr(agent, "last_tool_call_count", 0)
        tool_count = raw_count if type(raw_count) is int and raw_count >= 0 else 0
        tool_count = min(tool_count, remaining_budget)
        total_tool_calls += tool_count
        names = getattr(agent, "last_tool_call_names", [])
        tool_names = [
            name for name in names
            if isinstance(name, str) and name
        ] if isinstance(names, list) else []
        tool_failures = getattr(agent, "last_tool_call_failures", 0)
        if type(tool_failures) is not int or tool_failures < 0:
            tool_failures = 0
        verification_succeeded = bool(getattr(agent, "last_verification_succeeded", False))
        outcome = str(getattr(agent, "last_outcome", "failed")).lower()
        safe_answer = str(answer or "").strip()[:MAX_STEP_RESULT_CHARS]
        outputs.append(f"Step {index + 1}: {title}\n{safe_answer or '(No step result returned.)'}")

        if cancel_event.is_set() or outcome == "cancelled":
            task_store.update_plan_step(
                task_id,
                step_id,
                status="unverified",
                evidence="none",
                verification_note="Cancellation occurred during this step; its real-world state may be partial.",
                outcome="cancelled",
            )
            final_status = "cancelled"
            stop_reason = "Task cancellation was received; remaining steps were not started."
            break

        if outcome == "failed":
            task_store.update_plan_step(
                task_id,
                step_id,
                status="failed",
                evidence="none",
                verification_note="The assistant reported a failure while executing this step.",
                outcome="failed",
            )
            final_status = "partial" if completed_count or total_tool_calls else "failed"
            stop_reason = "A plan step failed; later steps were not started."
            break

        if outcome == "partial" or tool_failures:
            task_store.update_plan_step(
                task_id,
                step_id,
                status="unverified",
                evidence="tool_result" if tool_count else "none",
                verification_note="The step returned a partial result or tool error; completion was not verified.",
                outcome="partial",
            )
            final_status = "partial"
            stop_reason = "A plan step was only partially executed; later steps were not started."
            break

        if tool_count == 0:
            # Text-only steps deliver their output directly in the assistant response.
            task_store.update_plan_step(
                task_id,
                step_id,
                status="completed",
                evidence="assistant_response",
                verification_note="A text response was produced; no tool action was started for this step.",
                outcome="completed",
            )
            completed_count += 1
            continue

        if verification_succeeded:
            task_store.update_plan_step(
                task_id,
                step_id,
                status="completed",
                evidence="verified_local_action",
                verification_note="A deterministic local verification returned a positive result during this step.",
                outcome="completed",
            )
            completed_count += 1
            continue

        if tool_names and all(name in READ_ONLY_TOOL_NAMES for name in tool_names):
            task_store.update_plan_step(
                task_id,
                step_id,
                status="completed",
                evidence="tool_result",
                verification_note="Read-only tool results were returned; no local state change was claimed.",
                outcome="completed",
            )
            completed_count += 1
            continue

        task_store.update_plan_step(
            task_id,
            step_id,
            status="unverified",
            evidence="tool_result",
            verification_note=(
                "A tool returned, but no positive deterministic verification was recorded. "
                "Later steps were not started to avoid relying on an uncertain state."
            ),
            outcome="partial",
        )
        final_status = "partial"
        stop_reason = (
            "A tool action returned without a positive deterministic verification. "
            "Later steps were not started to avoid duplicating or depending on an uncertain action."
        )
        report(f"Plan step {index + 1} has no positive verification; pausing the plan safely")
        break

    if cancel_event.is_set():
        final_status = "cancelled"

    if final_status == "completed" and completed_count != len(plan_steps):
        final_status = "partial"
        stop_reason = stop_reason or "Not every planned step produced completion evidence."

    result = "\n\n".join(outputs).strip()
    if stop_reason:
        result += ("\n\nTASK PLAN PAUSED: " if final_status != "cancelled" else "\n\nTASK PLAN CANCELLED: ") + stop_reason
    if not result:
        result = stop_reason or "The task plan did not execute any steps."
    if len(result) > MAX_PLAN_RESULT_CHARS:
        result = result[: MAX_PLAN_RESULT_CHARS - 32].rstrip() + "\n\n[Remaining step output omitted.]"
    return result, final_status
