from __future__ import annotations

import json
import math
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from . import automation
from .settings import get_api_key, is_local_api_endpoint, validate_api_key_transport
from .safe_errors import safe_tool_error

MAX_TOOL_CALLS_PER_TASK = 12
READ_ONLY_TOOL_NAMES = frozenset({
    "search_files", "get_system_info", "list_open_windows", "get_active_window_title",
    "search_file_contents", "find_duplicate_files", "read_text_file",
})
STATE_CHANGING_TOOL_NAMES = frozenset({
    "open_application", "open_website", "prepare_whatsapp_message", "prepare_email_draft",
    "prepare_calendar_event_draft", "open_folder", "paste_text_into_window",
    "press_allowed_shortcut", "create_folder", "create_folder_structure", "create_text_file",
    "copy_file", "move_file", "rename_file", "create_zip_archive",
    "move_file_to_recycle_bin", "open_file",
})


def _verification_target(kind: object, target: object, location: object = "") -> tuple[str, str, str] | None:
    """Normalize a local verification target without storing or exposing it."""
    safe_kind = " ".join(str(kind or "").casefold().split())
    safe_target = " ".join(str(target or "").replace("\\", "/").split()).strip(" /").casefold()
    safe_location = " ".join(str(location or "").casefold().split())
    if safe_kind not in {"window", "file", "folder"} or not safe_target:
        return None
    return safe_kind, safe_target, safe_location if safe_kind != "window" else ""


def _expected_verification_targets(name: str, args: dict[str, Any]) -> set[tuple[str, str, str]]:
    """Return the exact local checks that can prove a supported state-changing action."""
    def target(kind: str, value: object, location: object = "") -> set[tuple[str, str, str]]:
        normalized = _verification_target(kind, value, location)
        return {normalized} if normalized else set()

    location = str(args.get("location", "Desktop") or "Desktop")
    if name == "open_application":
        return target("window", args.get("app_name"))
    if name == "open_website":
        value = str(args.get("url_or_query", "") or "").strip()
        folded = value.casefold()
        # Known aliases have recognizable human-readable tab titles; using the alias
        # avoids pretending "Google" is the target for Gmail/Drive/etc.
        for mapping_name in ("SOCIAL_WEBSITE_ALIASES", "WORKSPACE_WEBSITE_ALIASES"):
            aliases = getattr(automation, mapping_name, {})
            if isinstance(aliases, dict) and folded in aliases:
                return target("window", folded)
        parsed = None
        if "://" in value:
            parsed = urlparse(value)
        elif value and " " not in value and "." in value:
            # A host may be supplied without a scheme (e.g. example.com).
            # Plain-language search queries still open the search provider.
            parsed = urlparse("https://" + value)
        expected = parsed.hostname if parsed is not None else ""
        expected = expected or ("Google" if value else "")
        if expected.startswith("www."):
            expected = expected[4:]
        return target("window", expected)
    if name == "open_folder":
        return target("window", location)
    if name in {"create_folder"}:
        return target("folder", args.get("name"), location)
    if name == "create_folder_structure":
        paths = args.get("folder_paths")
        if not isinstance(paths, list) or not paths:
            return set()
        checks: set[tuple[str, str, str]] = set()
        for path in paths:
            checks.update(target("folder", path, location))
        # Empty/invalid items mean we cannot prove the whole structure was created.
        return checks if len(checks) == len(paths) else set()
    if name == "create_text_file":
        return target("file", args.get("filename"), location)
    if name in {"copy_file", "move_file"}:
        destination = str(args.get("destination_location", "") or "")
        filename = args.get("destination_filename")
        return target("file", filename, destination)
    if name == "rename_file":
        return target("file", args.get("new_filename"), location)
    if name == "create_zip_archive":
        return target("file", args.get("archive_filename"), location)
    if name == "open_file":
        return target("window", args.get("filename"))
    # These actions need stronger evidence than a generic visible-window title can give:
    # a draft can be empty, text can be pasted into the wrong field, and Recycle Bin absence
    # does not prove an item was recoverably moved rather than deleted. Fail closed.
    return set()


SYSTEM_PROMPT = """You are J.A.R.V.I.S, a careful desktop personal assistant for a Windows 11 user. Speak naturally and warmly, matching the user's language (Bangla or English). Be concise but useful. Your primary purpose is to complete supported user requests, not merely describe how to do them: when the user asks you to perform an action and a supplied tool can do it safely, call the tool, inspect its result, verify outcomes with verify_local_action when a deterministic check exists, and then report what is completed, partially completed, or blocked. For multi-step requests, continue the tool workflow rather than stopping at a plan. You may use only the tools explicitly provided. Never claim an action succeeded unless the tool result confirms it. After a meaningful app/file/folder action, use verify_local_action when the result can be checked with an allowed deterministic signal; distinguish 'requested/launched' from 'verified'. For potentially destructive or external actions, explain the action and ask for approval first; moving a file to the Recycle Bin requires explicit, action-specific approval and must never be described as permanent deletion; reading local file contents, creating, copying, moving, or renaming files requires explicit, action-specific approval. Before reading a file, the approval dialog must show the exact path and size and warn that contents enter the AI conversation and may be sent to the configured AI provider. File operations are restricted to regular files inside Desktop, Documents, or Downloads; symbolic links are blocked and existing destinations must never be overwritten. Creating a ZIP may include up to 100 user-selected regular files from one approved folder, capped at 100 MiB total, with explicit approval and no-overwrite publication. Duplicate-file scans operate only in Desktop/Documents/Downloads (or All), require approval, hash bounded same-size candidates locally, report shortened hashes and file paths, and never modify or delete files. Only search file contents when the user asks to search inside files; search results require explicit approval and disclose that short matching excerpts enter the AI conversation. Do not ask for or expose passwords, API keys, or private credentials. Never attempt to bypass security, antivirus, permissions, or user consent. For foreground-window text or shortcut actions, inspect the visible window title, specify the intended target window, request the explicit approval supplied by the tool, never press Enter to submit a form, and never claim text insertion has been independently verified. You cannot control every app or perform literally every possible task. For unsupported tasks, explain the limitation honestly and suggest a safe next step. Prefer Bangla if the user writes in Bangla."""


_PROVIDER_RETRYABLE_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
_PROVIDER_MAX_ATTEMPTS = 3
_PROVIDER_MAX_RETRY_AFTER_SECONDS = 5.0


def _provider_retry_delay(response: Any, failed_attempt: int) -> float | None:
    """Return a bounded retry delay; None means the provider asked us to wait too long."""
    headers = getattr(response, "headers", {})
    raw_retry_after = str(headers.get("Retry-After", "")).strip() if hasattr(headers, "get") else ""
    if raw_retry_after:
        delay: float | None = None
        try:
            delay = float(raw_retry_after)
        except (TypeError, ValueError, OverflowError):
            try:
                retry_at = parsedate_to_datetime(raw_retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = (retry_at - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                delay = None
        if delay is not None and math.isfinite(delay):
            delay = max(0.0, delay)
            # Never violate a long Retry-After by retrying early; surface the safe HTTP error instead.
            return delay if delay <= _PROVIDER_MAX_RETRY_AFTER_SECONDS else None
    return min(0.5 * (2 ** max(0, failed_attempt - 1)), 2.0)


def _wait_before_provider_retry(delay: float, cancel_event: threading.Event | None) -> bool:
    """Wait interruptibly when possible; return False when the user cancels during backoff."""
    if cancel_event is not None:
        return not cancel_event.wait(max(0.0, delay))
    if delay > 0:
        time.sleep(delay)
    return True


def _post_with_bounded_retry(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: tuple[int, int] = (10, 45),
    cancel_event: threading.Event | None = None,
    progress: Callable[[str], None] | None = None,
    max_attempts: int = _PROVIDER_MAX_ATTEMPTS,
) -> requests.Response | None:
    """Retry only transient model-provider requests, before any returned tool is executed.

    The retry budget is deliberately small. Tool actions are never replayed here, and
    HTTP failures outside the explicit transient allow-list are returned immediately.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least one")

    def report_retry(message: str) -> None:
        if progress is not None:
            try:
                progress(message)
            except Exception:
                pass

    for attempt in range(1, max_attempts + 1):
        if cancel_event is not None and cancel_event.is_set():
            return None
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt >= max_attempts:
                raise
            delay = min(0.5 * (2 ** (attempt - 1)), 2.0)
            report_retry(
                f"AI provider connection timed out or failed; retrying request {attempt + 1}/{max_attempts} after {delay:.1f}s"
            )
            if not _wait_before_provider_retry(delay, cancel_event):
                return None
            continue

        status_code = int(getattr(response, "status_code", 0) or 0)
        if status_code not in _PROVIDER_RETRYABLE_STATUSES or attempt >= max_attempts:
            return response

        delay = _provider_retry_delay(response, attempt)
        if delay is None:
            return response
        report_retry(
            f"AI provider returned transient HTTP {status_code}; retrying request {attempt + 1}/{max_attempts} after {delay:.1f}s"
        )
        if not _wait_before_provider_retry(delay, cancel_event):
            return None

    return None

def _safe_provider_http_error(status_code: int) -> str:
    """Return actionable HTTP diagnostics without reflecting provider-controlled response bodies."""
    messages = {
        400: "The provider rejected the request. Check the model name, endpoint format, and tool-calling support.",
        401: "Authentication failed. Check the API key in Settings.",
        403: "The provider denied access. Check API-key permissions and model access.",
        404: "The endpoint or model was not found. Check the API base URL and model name.",
        408: "The provider timed out. Try again or use a shorter request.",
        413: "The request was too large for the provider. Try a shorter request or a model with a larger context window.",
        429: "The provider rate limit or quota was reached. Check usage limits before retrying.",
        500: "The provider encountered an internal error. Try again later.",
        502: "The provider gateway returned an error. Check service status and try again.",
        503: "The provider is temporarily unavailable. Try again later.",
        504: "The provider gateway timed out. Try again later.",
    }
    advice = messages.get(status_code, "Check the endpoint, provider status, and model permissions.")
    return (
        f"AI provider returned HTTP {status_code}. {advice} "
        "The raw response body is hidden to protect prompt content and credentials."
    )


def _invalid_provider_response(message: str = "AI provider returned an invalid or unsupported response format.") -> str:
    """Keep malformed provider payloads from raising errors in the desktop UI."""
    return message



TOOLS: list[dict[str, Any]] = [
    {"type": "function", "function": {"name": "open_application", "description": "Open an allowlisted Windows application such as Notepad, Calculator, Paint, File Explorer, Task Manager, Word, Excel, PowerPoint, Outlook, OneNote, Snipping Tool, VS Code, the default browser, or Windows Settings.", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
    {"type": "function", "function": {"name": "open_website", "description": "Open an HTTP(S) website or search Google for a query in the default browser.", "parameters": {"type": "object", "properties": {"url_or_query": {"type": "string"}}, "required": ["url_or_query"]}}},
    {"type": "function", "function": {"name": "prepare_whatsapp_message", "description": "Open WhatsApp Web with a message prefilled for an international phone number. This never sends the message; clearly tell the user to review recipient and text and click Send manually.", "parameters": {"type": "object", "properties": {"phone_number": {"type": "string", "description": "Recipient phone number including country calling code, 8–15 digits; may include +, spaces, or hyphens."}, "message": {"type": "string", "description": "Message text to prefill, up to 4,000 characters."}}, "required": ["phone_number", "message"]}}},
    {"type": "function", "function": {"name": "prepare_email_draft", "description": "Open the default email application with a prefilled draft. This never sends email; tell the user to review and send manually.", "parameters": {"type": "object", "properties": {"recipient": {"type": "string", "description": "One recipient email address."}, "subject": {"type": "string", "description": "Email subject, up to 200 characters; may be empty."}, "body": {"type": "string", "description": "Email body, 1–5,000 characters."}}, "required": ["recipient", "subject", "body"]}}},
    {"type": "function", "function": {"name": "prepare_calendar_event_draft", "description": "Open a Google Calendar event template for review; never save an event or send invitations automatically.", "parameters": {"type": "object", "properties": {"title": {"type": "string", "description": "Event title, 1–200 characters."}, "start": {"type": "string", "description": "Local ISO datetime such as 2026-10-26T14:30, without timezone offset."}, "end": {"type": "string", "description": "Local ISO datetime later than start."}, "details": {"type": "string", "description": "Optional event details, up to 4,000 characters."}, "location": {"type": "string", "description": "Optional location, up to 300 characters."}, "timezone_name": {"type": "string", "description": "Supported timezone, default Asia/Dhaka."}}, "required": ["title", "start", "end"]}}},
    {"type": "function", "function": {"name": "open_folder", "description": "Open the user's Desktop, Documents, or Downloads folder in File Explorer.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}}, "required": ["location"]}}},
    {"type": "function", "function": {"name": "search_files", "description": "Search filenames under Desktop, Documents, and Downloads. Does not read file content.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_system_info", "description": "Get basic OS, computer, Python, and current-time information.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "list_open_windows", "description": "List the titles of visible Windows application windows. This reads titles only, not screenshots, text fields, or app contents.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "get_active_window_title", "description": "Read the active Windows application window title only; does not inspect its contents.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "verify_local_action", "description": "Verify an exact file/folder name inside Desktop, Documents or Downloads, or verify that a visible Windows app window title contains a given fragment. Use after the related action when possible. This checks existence/title only, not file contents or whether a user-visible task was fully completed.", "parameters": {"type": "object", "properties": {"kind": {"type": "string", "enum": ["window", "file", "folder"]}, "target": {"type": "string"}, "location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}}, "required": ["kind", "target"]}}},
    {"type": "function", "function": {"name": "paste_text_into_window", "description": "Paste provided text into the current field of a named visible Windows window. Always needs explicit user approval and will not press Enter or submit a form. Select the target using a distinctive substring from list_open_windows.", "parameters": {"type": "object", "properties": {"expected_app": {"type": "string"}, "text": {"type": "string"}}, "required": ["expected_app", "text"]}}},
    {"type": "function", "function": {"name": "press_allowed_shortcut", "description": "Send one user-approved editing/navigation shortcut to a named Windows window. Only supported allow-listed shortcuts are accepted; Enter, Alt+F4, Windows+R and arbitrary key sequences are blocked.", "parameters": {"type": "object", "properties": {"expected_app": {"type": "string"}, "shortcut": {"type": "string", "enum": ["CTRL+S", "CTRL+A", "CTRL+C", "CTRL+V", "CTRL+Z", "CTRL+Y", "CTRL+F", "TAB", "SHIFT+TAB", "ESC", "HOME", "END", "PAGEUP", "PAGEDOWN"]}}, "required": ["expected_app", "shortcut"]}}},
    {"type": "function", "function": {"name": "create_folder", "description": "Create a folder inside Desktop, Documents, or Downloads. The desktop app will ask the user for confirmation.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "name": {"type": "string"}}, "required": ["location", "name"]}}},
    {"type": "function", "function": {"name": "create_folder_structure", "description": "Create multiple nested folders for a project under Desktop, Documents, or Downloads after one explicit approval. Accepts 1–30 relative paths, at most 8 levels deep; never overwrites existing items and verifies no destination already exists.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "folder_paths": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 30}}, "required": ["location", "folder_paths"]}}},
    {"type": "function", "function": {"name": "create_text_file", "description": "Create a new .txt, .md, .csv, .json, or .log file under Desktop, Documents, or Downloads, including inside an existing project subfolder using a relative path such as CivilOS/Reports/summary.md. The parent folder must already exist. No overwriting; asks for approval.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}, "content": {"type": "string"}}, "required": ["location", "filename", "content"]}}},
    {"type": "function", "function": {"name": "read_text_file", "description": "Read a small text/code file from Desktop, Documents, or Downloads after explicit user approval. The approval dialog explains that contents may be sent to the configured AI provider. Only common text formats up to 100 KB are supported; paths, symbolic links, and binary files are blocked.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}}, "required": ["location", "filename"]}}},

    {"type": "function", "function": {"name": "copy_file", "description": "Copy one regular file between Desktop, Documents, or Downloads. Requires explicit approval, blocks symbolic links, and never overwrites an existing destination.", "parameters": {"type": "object", "properties": {"source_location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}, "destination_location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "destination_filename": {"type": "string"}}, "required": ["source_location", "filename", "destination_location", "destination_filename"]}}},
    {"type": "function", "function": {"name": "move_file", "description": "Move one regular file between Desktop, Documents, or Downloads. Requires explicit approval; destination is created with no-overwrite protection, and the source is removed only after the copy succeeds.", "parameters": {"type": "object", "properties": {"source_location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}, "destination_location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "destination_filename": {"type": "string"}}, "required": ["source_location", "filename", "destination_location", "destination_filename"]}}},
    {"type": "function", "function": {"name": "rename_file", "description": "Rename one regular file inside Desktop, Documents, or Downloads. Requires explicit approval and never overwrites an existing destination.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}, "new_filename": {"type": "string"}}, "required": ["location", "filename", "new_filename"]}}},


    {"type": "function", "function": {"name": "search_file_contents", "description": "Search for a phrase inside common text/source files in Desktop, Documents, Downloads, or All. Requires explicit consent because short matching lines enter the AI context; reads only bounded text files and returns at most 20 matching excerpts.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads", "All"]}}, "required": ["query", "location"]}}},

    {"type": "function", "function": {"name": "find_duplicate_files", "description": "Find identical files by SHA-256 inside Desktop, Documents, Downloads, or All. Requires explicit approval. Recursively scans at most 5,000 file entries, hashes at most 256 MiB total and skips individual files above 100 MiB; excludes symlinks/hidden/generated folders. Returns only paths, sizes and shortened hashes, never edits or deletes files.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads", "All"]}}, "required": ["location"]}}},
    {"type": "function", "function": {"name": "create_zip_archive", "description": "Create a ZIP archive from 1 to 100 selected regular files in one of Desktop, Documents, or Downloads. Maximum combined source size is 100 MiB. Requires explicit approval listing every source and size; blocks paths, symlinks, duplicate names, changing files, and an existing archive destination. Source files remain unchanged.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filenames": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 100}, "archive_filename": {"type": "string"}}, "required": ["location", "filenames", "archive_filename"]}}},
    {"type": "function", "function": {"name": "move_file_to_recycle_bin", "description": "Move one regular file from Desktop, Documents, or Downloads to the Windows Recycle Bin (not permanent deletion). Requires explicit approval with exact path and size; blocks symbolic links, path traversal, directories, missing files, and files changed during confirmation.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}}, "required": ["location", "filename"]}}},
    {"type": "function", "function": {"name": "open_file", "description": "Open one existing document/data/image file from Desktop, Documents, or Downloads in its default Windows app. Requires explicit approval; scripts and executables are blocked.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}}, "required": ["location", "filename"]}}},
]


class JarvisAgent:
    def __init__(self, settings: dict[str, Any], approval: Callable[[str, str], bool]) -> None:
        self.settings = settings
        self.approval = approval
        self.history: list[dict[str, Any]] = []
        self.last_tool_call_count = 0
        self.last_tool_call_names: list[str] = []
        self.last_tool_call_failures = 0
        self.last_verification_succeeded = False

    def update_settings(self, settings: dict[str, Any]) -> None:
        self.settings = settings

    def respond(
        self,
        user_text: str,
        cancel_event: threading.Event | None = None,
        progress: Callable[[str], None] | None = None,
        tool_event: Callable[[str, str, str | None, str], str | None] | None = None,
        tool_budget: int = MAX_TOOL_CALLS_PER_TASK,
    ) -> str:
        """Answer a user request; cancellation is cooperative between blocking operations.

        tool_budget caps tool actions for this response, allowing a caller to enforce one
        aggregate budget across a multi-step task. Completion evidence is bounded metadata;
        tool arguments and results are never copied into these fields.
        """
        self.last_outcome = "completed"
        self.last_tool_call_count = 0
        self.last_tool_call_names = []
        self.last_tool_call_failures = 0
        self.last_verification_succeeded = False
        required_verification_targets: set[tuple[str, str, str]] = set()
        verified_targets: set[tuple[str, str, str]] = set()
        if type(tool_budget) is not int:
            tool_budget = MAX_TOOL_CALLS_PER_TASK
        max_tool_calls = min(MAX_TOOL_CALLS_PER_TASK, max(0, tool_budget))
        had_tool_failure = False

        def invalid_response(message: str = "AI provider returned an invalid or unsupported response format.") -> str:
            self.last_outcome = "failed"
            return _invalid_provider_response(message)

        def cancelled_response(answer: str) -> str:
            self.last_outcome = "cancelled"
            return answer

        def cancelled() -> bool:
            return cancel_event is not None and cancel_event.is_set()

        def report(step: str) -> None:
            if progress is not None:
                try:
                    progress(step)
                except Exception:
                    # Progress/history UI must never break the actual assistant workflow.
                    pass

        def notify_tool_event(
            name: str,
            status: str,
            action_id: str | None = None,
            note: str = "",
        ) -> str | None:
            if tool_event is None:
                return action_id
            try:
                return tool_event(name, status, action_id, note)
            except Exception as exc:
                # Audit/history failures must never interrupt the actual tool workflow.
                report(f"Tool action audit update failed ({type(exc).__name__})")
                return action_id

        if cancelled():
            return cancelled_response("কাজটি বাতিল করা হয়েছে। বাতিলের অনুরোধ পাওয়ার পর নতুন কোনো action শুরু করা হয়নি।")

        report("Checking supported local commands")
        direct = automation.direct_command(user_text)
        if direct is not None:
            if cancelled():
                return cancelled_response("বাতিলের অনুরোধ local command চলার সময় এসেছে। Command-এর ফল ইতিমধ্যে ঘটতে পারে: " + direct)
            return direct
        if cancelled():
            return cancelled_response("কাজটি বাতিল করা হয়েছে। কোনো নতুন AI tool action চালানো হয়নি।")

        base_url = str(self.settings.get("api_base_url", "")).strip().rstrip("/")
        model = str(self.settings.get("model", "")).strip()
        if not base_url or not model:
            self.last_outcome = "failed"
            return "AI model সেট করা নেই। Settings-এ API endpoint ও model দিন, অথবা local AI চাইলে Ollama ইনস্টল করে সেটি চালু করুন। সাধারণ app/website কমান্ড API ছাড়াও কাজ করবে।"

        key = get_api_key()
        try:
            base_url = validate_api_key_transport(base_url, key)
            is_local = is_local_api_endpoint(base_url)
        except ValueError as exc:
            self.last_outcome = "failed"
            return f"AI endpoint setting blocked for security: {exc}"
        if not is_local and not key:
            self.last_outcome = "failed"
            return "AI API key পাওয়া যায়নি। Settings খুলে provider-এর API key দিন। Local Ollama ব্যবহার করলে API key ফাঁকা রাখা যাবে।"

        self.history.append({"role": "user", "content": user_text})
        self.history = self.history[-18:]
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        url = base_url + "/chat/completions"
        max_rounds = 8
        tool_call_count = 0
        try:
            for turn in range(max_rounds):
                if cancelled():
                    return cancelled_response("কাজটি বাতিল করা হয়েছে। আর কোনো tool action চালানো হবে না।")
                report(f"Contacting AI model (turn {turn + 1}/{max_rounds})")
                response = _post_with_bounded_retry(
                    url,
                    headers=headers,
                    payload={"model": model, "messages": messages, "tools": TOOLS, "tool_choice": "auto", "temperature": 0.4},
                    timeout=(10, 45),
                    cancel_event=cancel_event,
                    progress=report,
                )
                if response is None and cancelled():
                    return cancelled_response("কাজ বাতিলের অনুরোধ গৃহীত হয়েছে। নতুন কোনো tool action চালানো হয়নি।")
                # requests cannot interrupt an already-blocked network read; after it
                # returns, cancellation is checked before any model-requested tool runs.
                if cancelled():
                    return cancelled_response("কাজ বাতিলের অনুরোধ গৃহীত হয়েছে। বর্তমান AI request শেষ হওয়ার পরে কোনো নতুন tool action চালানো হয়নি।")
                if response.status_code >= 400:
                    self.last_outcome = "failed"
                    return _safe_provider_http_error(int(response.status_code))
                try:
                    payload = response.json()
                except (ValueError, requests.RequestException):
                    return invalid_response(
                        "AI provider returned invalid JSON. Check endpoint compatibility; response content was hidden."
                    )
                if not isinstance(payload, dict):
                    return invalid_response()
                choices = payload.get("choices")
                if not isinstance(choices, list):
                    return invalid_response("AI provider response is missing a valid choices list.")
                if not choices:
                    self.last_outcome = "failed"
                    return "AI provider কোনো উত্তর দেয়নি। Model/endpoint Settings-এ যাচাই করো।"
                choice = choices[0]
                if not isinstance(choice, dict):
                    return invalid_response("AI provider returned a malformed choice object.")
                message = choice.get("message")
                if not isinstance(message, dict):
                    return invalid_response("AI provider response is missing a valid message object.")
                tool_calls = message.get("tool_calls") or []
                if not isinstance(tool_calls, list):
                    return invalid_response("AI provider returned malformed tool-call data.")
                for tool_call in tool_calls:
                    if not isinstance(tool_call, dict) or not isinstance(tool_call.get("function", {}), dict):
                        return invalid_response("AI provider returned malformed tool-call data.")
                    arguments = tool_call["function"].get("arguments", "{}")
                    if not isinstance(arguments, (str, dict)):
                        return invalid_response("AI provider returned malformed tool arguments.")
                messages.append(message)
                if not tool_calls:
                    content = message.get("content")
                    if content is None or content == "":
                        answer = "আমি উত্তর তৈরি করতে পারিনি। আরেকবার বলো।"
                        self.last_outcome = "failed"
                    elif isinstance(content, str):
                        answer = content
                        self.last_outcome = "partial" if had_tool_failure else "completed"
                    else:
                        return invalid_response("AI provider returned an unsupported answer content type.")
                    self.history.append({"role": "assistant", "content": answer})
                    return answer
                for call in tool_calls:
                    if cancelled():
                        return cancelled_response("কাজটি বাতিল করা হয়েছে। বাতিলের পরে আর কোনো নতুন tool action চালানো হয়নি।")
                    if tool_call_count >= max_tool_calls:
                        self.last_outcome = "partial"
                        report(f"Task action budget reached ({max_tool_calls} action limit); no further tools will start")
                        return (
                            f"Partially completed: নিরাপত্তার জন্য এই task-এর {max_tool_calls}টি tool action সীমা পৌঁছেছে। "
                            "যে ফলাফলগুলো পাওয়া গেছে তা যাচাই করো, তারপর বাকি কাজের জন্য নতুন নির্দেশনা দাও।"
                        )
                    tool_call_count += 1
                    self.last_tool_call_count = tool_call_count
                    function = call.get("function", {})
                    name = str(function.get("name", "") or "")[:80] or "unknown"
                    self.last_tool_call_names.append(name)
                    raw_args = function.get("arguments", "{}")
                    report(f"Running tool: {name or 'unknown'}")
                    audit_id = notify_tool_event(name or "unknown", "running")
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                        if not isinstance(args, dict):
                            raise ValueError("Tool arguments must be an object.")
                        if name in STATE_CHANGING_TOOL_NAMES:
                            # Any later side effect invalidates prior checks. Keep target details
                            # in memory only; the task audit still stores no arguments/results.
                            required_verification_targets.update(
                                _expected_verification_targets(name, args)
                            )
                            if not _expected_verification_targets(name, args):
                                required_verification_targets.add(("unverifiable", name, ""))
                            verified_targets.clear()
                            self.last_verification_succeeded = False
                        result = self._execute_tool(name, args)
                    except Exception as exc:
                        had_tool_failure = True
                        self.last_tool_call_failures += 1
                        result = safe_tool_error(exc)
                        notify_tool_event(name or "unknown", "failed", audit_id, type(exc).__name__)
                    else:
                        # Store only the fact that the tool returned; never copy its arguments or payload.
                        notify_tool_event(name or "unknown", "result_received", audit_id)
                        if (
                            name == "verify_local_action"
                            and isinstance(result, str)
                            and result.strip().casefold().startswith("verified")
                            and isinstance(args, dict)
                        ):
                            actual_target = _verification_target(
                                args.get("kind"),
                                args.get("target"),
                                args.get("location", "Desktop"),
                            )
                            if actual_target is not None and actual_target in required_verification_targets:
                                verified_targets.add(actual_target)
                            self.last_verification_succeeded = (
                                bool(required_verification_targets)
                                and ("unverifiable", "", "") not in required_verification_targets
                                and all(
                                    requirement in verified_targets
                                    for requirement in required_verification_targets
                                    if requirement[0] != "unverifiable"
                                )
                                and not any(item[0] == "unverifiable" for item in required_verification_targets)
                            )
                    messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "name": name, "content": str(result)[:12000]})
                    # Do not copy tool output into progress history; it may contain paths or user data.
                    report(f"Tool returned: {name or 'unknown'}")
                    if cancelled():
                        return cancelled_response("কাজটি বাতিল করা হয়েছে। বর্তমানে চলমান action ফিরিয়ে নেওয়া যায় না, তবে এরপর আর কোনো tool action শুরু করা হয়নি।")
            self.last_outcome = "partial"
            return "Partially completed: এই task-এ ৮টি AI action round-এর সীমা পৌঁছেছে। Task History ও progress দেখো; বাকি কাজ নতুন নির্দেশনায় চালাও।"
        except requests.exceptions.ConnectionError:
            self.last_outcome = "failed"
            return "AI model-এ সংযোগ করা যাচ্ছে না। Local Ollama ব্যবহার করলে Ollama চালু আছে কি না ও model pull করা হয়েছে কি না দেখো; cloud provider হলে internet, endpoint ও API key যাচাই করো।"
        except requests.exceptions.Timeout:
            self.last_outcome = "failed"
            return "AI model উত্তর দিতে বেশি সময় নিয়েছে। আবার চেষ্টা করো অথবা ছোট নির্দেশনা দাও।"
        except requests.RequestException as exc:
            # Network exception strings can include URLs or provider-controlled text; never echo them.
            self.last_outcome = "failed"
            return f"AI request failed safely ({type(exc).__name__}). Check your network and endpoint settings."
        except (ValueError, KeyError, TypeError, AttributeError):
            return invalid_response()
        except Exception as exc:
            # Keep an unexpected adapter/library failure from escaping into the Tkinter worker.
            self.last_outcome = "failed"
            report(f"Unexpected AI request failure: {type(exc).__name__}")
            return f"AI request failed safely ({type(exc).__name__}). Check endpoint settings and try again."

    def _execute_tool(self, name: str, args: dict[str, Any]) -> str:
        if name == "open_application":
            return automation.open_application(str(args.get("app_name", "")))
        if name == "open_website":
            return automation.open_website(str(args.get("url_or_query", "")))
        if name == "prepare_whatsapp_message":
            return automation.prepare_whatsapp_message(
                str(args.get("phone_number", "")), str(args.get("message", ""))
            )
        if name == "prepare_email_draft":
            return automation.prepare_email_draft(
                str(args.get("recipient", "")),
                str(args.get("subject", "")),
                str(args.get("body", "")),
            )
        if name == "prepare_calendar_event_draft":
            return automation.prepare_calendar_event_draft(
                str(args.get("title", "")),
                str(args.get("start", "")),
                str(args.get("end", "")),
                str(args.get("details", "")),
                str(args.get("location", "")),
                str(args.get("timezone_name", "Asia/Dhaka")),
            )
        if name == "open_folder":
            return automation.open_folder(str(args.get("location", "")))
        if name == "search_files":
            return automation.search_files(str(args.get("query", "")))
        if name == "get_system_info":
            return automation.get_system_info()
        if name == "list_open_windows":
            return automation.list_open_windows()
        if name == "get_active_window_title":
            return automation.get_active_window_title()
        if name == "verify_local_action":
            return automation.verify_local_action(
                str(args.get("kind", "")),
                str(args.get("target", "")),
                str(args.get("location", "Desktop")),
            )
        if name == "paste_text_into_window":
            return automation.paste_text_into_window(
                str(args.get("text", "")), str(args.get("expected_app", "")), self.approval
            )
        if name == "press_allowed_shortcut":
            return automation.press_allowed_shortcut(
                str(args.get("shortcut", "")), str(args.get("expected_app", "")), self.approval
            )
        if name == "create_folder":
            return automation.create_folder(str(args.get("location", "")), str(args.get("name", "")), self.approval)
        if name == "create_folder_structure":
            raw_paths = args.get("folder_paths", [])
            if not isinstance(raw_paths, list):
                return "Folder structure blocked: folder_paths must be a list of relative paths."
            return automation.create_folder_structure(str(args.get("location", "")), raw_paths, self.approval)
        if name == "create_text_file":
            return automation.create_text_file(str(args.get("location", "")), str(args.get("filename", "")), str(args.get("content", "")), self.approval)
        if name == "read_text_file":
            return automation.read_text_file(
                str(args.get("location", "")),
                str(args.get("filename", "")),
                self.approval,
            )
        if name == "search_file_contents":
            return automation.search_file_contents(
                str(args.get("query", "")),
                str(args.get("location", "All")),
                self.approval,
            )
        if name == "find_duplicate_files":
            return automation.find_duplicate_files(
                str(args.get("location", "All")),
                self.approval,
            )
        if name == "create_zip_archive":
            raw_filenames = args.get("filenames", [])
            if not isinstance(raw_filenames, list):
                return "ZIP creation blocked: filenames must be a list of simple filenames."
            return automation.create_zip_archive(
                str(args.get("location", "")),
                raw_filenames,
                str(args.get("archive_filename", "")),
                self.approval,
            )
        if name == "move_file_to_recycle_bin":
            return automation.move_file_to_recycle_bin(
                str(args.get("location", "")),
                str(args.get("filename", "")),
                self.approval,
            )
        if name == "open_file":
            return automation.open_file(
                str(args.get("location", "")),
                str(args.get("filename", "")),
                self.approval,
            )
        if name == "copy_file":
            return automation.copy_file(
                str(args.get("source_location", "")),
                str(args.get("filename", "")),
                str(args.get("destination_location", "")),
                str(args.get("destination_filename", "")),
                self.approval,
            )
        if name == "move_file":
            return automation.move_file(
                str(args.get("source_location", "")),
                str(args.get("filename", "")),
                str(args.get("destination_location", "")),
                str(args.get("destination_filename", "")),
                self.approval,
            )
        if name == "rename_file":
            return automation.rename_file(
                str(args.get("location", "")),
                str(args.get("filename", "")),
                str(args.get("new_filename", "")),
                self.approval,
            )
        return f"Unknown tool '{name}' was blocked."
