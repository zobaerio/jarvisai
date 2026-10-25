from __future__ import annotations

import json
import threading
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from . import automation
from .settings import get_api_key

SYSTEM_PROMPT = """You are J.A.R.V.I.S, a careful desktop personal assistant for a Windows 11 user. Speak naturally and warmly, matching the user's language (Bangla or English). Be concise but useful. Your primary purpose is to complete supported user requests, not merely describe how to do them: when the user asks you to perform an action and a supplied tool can do it safely, call the tool, inspect its result, verify outcomes with verify_local_action when a deterministic check exists, and then report what is completed, partially completed, or blocked. For multi-step requests, continue the tool workflow rather than stopping at a plan. You may use only the tools explicitly provided. Never claim an action succeeded unless the tool result confirms it. After a meaningful app/file/folder action, use verify_local_action when the result can be checked with an allowed deterministic signal; distinguish 'requested/launched' from 'verified'. For potentially destructive or external actions, explain the action and ask for approval first; creating, copying, moving, or renaming files requires an explicit, action-specific approval. File operations are restricted to one regular file inside Desktop, Documents, or Downloads, symbolic links are blocked, and existing destinations must never be overwritten. Only search file contents when the user asks to search inside files; search results require explicit approval and disclose that short matching excerpts enter the AI conversation. Do not ask for or expose passwords, API keys, or private credentials. Never attempt to bypass security, antivirus, permissions, or user consent. For foreground-window text or shortcut actions, inspect the visible window title, specify the intended target window, request the explicit approval supplied by the tool, never press Enter to submit a form, and never claim text insertion has been independently verified. You cannot control every app or perform literally every possible task. For unsupported tasks, explain the limitation honestly and suggest a safe next step. Prefer Bangla if the user writes in Bangla."""

TOOLS: list[dict[str, Any]] = [
    {"type": "function", "function": {"name": "open_application", "description": "Open an allowlisted Windows application such as Notepad, Calculator, Paint, File Explorer, Task Manager, Word, Excel, PowerPoint, Outlook, OneNote, Snipping Tool, VS Code, the default browser, or Windows Settings.", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
    {"type": "function", "function": {"name": "open_website", "description": "Open an HTTP(S) website or search Google for a query in the default browser.", "parameters": {"type": "object", "properties": {"url_or_query": {"type": "string"}}, "required": ["url_or_query"]}}},
    {"type": "function", "function": {"name": "open_folder", "description": "Open the user's Desktop, Documents, or Downloads folder in File Explorer.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}}, "required": ["location"]}}},
    {"type": "function", "function": {"name": "search_files", "description": "Search filenames under Desktop, Documents, and Downloads. Does not read file content.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_system_info", "description": "Get basic OS, computer, Python, and current-time information.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "list_open_windows", "description": "List the titles of visible Windows application windows. This reads titles only, not screenshots, text fields, or app contents.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "get_active_window_title", "description": "Read the active Windows application window title only; does not inspect its contents.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "verify_local_action", "description": "Verify an exact file/folder name inside Desktop, Documents or Downloads, or verify that a visible Windows app window title contains a given fragment. Use after the related action when possible. This checks existence/title only, not file contents or whether a user-visible task was fully completed.", "parameters": {"type": "object", "properties": {"kind": {"type": "string", "enum": ["window", "file", "folder"]}, "target": {"type": "string"}, "location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}}, "required": ["kind", "target"]}}},
    {"type": "function", "function": {"name": "paste_text_into_window", "description": "Paste provided text into the current field of a named visible Windows window. Always needs explicit user approval and will not press Enter or submit a form. Select the target using a distinctive substring from list_open_windows.", "parameters": {"type": "object", "properties": {"expected_app": {"type": "string"}, "text": {"type": "string"}}, "required": ["expected_app", "text"]}}},
    {"type": "function", "function": {"name": "press_allowed_shortcut", "description": "Send one user-approved editing/navigation shortcut to a named Windows window. Only supported allow-listed shortcuts are accepted; Enter, Alt+F4, Windows+R and arbitrary key sequences are blocked.", "parameters": {"type": "object", "properties": {"expected_app": {"type": "string"}, "shortcut": {"type": "string", "enum": ["CTRL+S", "CTRL+A", "CTRL+C", "CTRL+V", "CTRL+Z", "CTRL+Y", "CTRL+F", "TAB", "SHIFT+TAB", "ESC", "HOME", "END", "PAGEUP", "PAGEDOWN"]}}, "required": ["expected_app", "shortcut"]}}},
    {"type": "function", "function": {"name": "create_folder", "description": "Create a folder inside Desktop, Documents, or Downloads. The desktop app will ask the user for confirmation.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "name": {"type": "string"}}, "required": ["location", "name"]}}},
    {"type": "function", "function": {"name": "create_text_file", "description": "Create a new .txt, .md, .csv, .json, or .log file under Desktop, Documents, or Downloads. No overwriting. The app asks the user for confirmation.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}, "content": {"type": "string"}}, "required": ["location", "filename", "content"]}}},
    {"type": "function", "function": {"name": "read_text_file", "description": "Read a small text/code file from Desktop, Documents, or Downloads. Provide the exact filename within the selected folder. Only common text formats are supported.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}}, "required": ["location", "filename"]}}},

    {"type": "function", "function": {"name": "copy_file", "description": "Copy one regular file between Desktop, Documents, or Downloads. Requires explicit approval, blocks symbolic links, and never overwrites an existing destination.", "parameters": {"type": "object", "properties": {"source_location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}, "destination_location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "destination_filename": {"type": "string"}}, "required": ["source_location", "filename", "destination_location", "destination_filename"]}}},
    {"type": "function", "function": {"name": "move_file", "description": "Move one regular file between Desktop, Documents, or Downloads. Requires explicit approval; destination is created with no-overwrite protection, and the source is removed only after the copy succeeds.", "parameters": {"type": "object", "properties": {"source_location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}, "destination_location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "destination_filename": {"type": "string"}}, "required": ["source_location", "filename", "destination_location", "destination_filename"]}}},
    {"type": "function", "function": {"name": "rename_file", "description": "Rename one regular file inside Desktop, Documents, or Downloads. Requires explicit approval and never overwrites an existing destination.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}, "new_filename": {"type": "string"}}, "required": ["location", "filename", "new_filename"]}}},


    {"type": "function", "function": {"name": "search_file_contents", "description": "Search for a phrase inside common text/source files in Desktop, Documents, Downloads, or All. Requires explicit consent because short matching lines enter the AI context; reads only bounded text files and returns at most 20 matching excerpts.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads", "All"]}}, "required": ["query", "location"]}}},

    {"type": "function", "function": {"name": "open_file", "description": "Open one existing document/data/image file from Desktop, Documents, or Downloads in its default Windows app. Requires explicit approval; scripts and executables are blocked.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "enum": ["Desktop", "Documents", "Downloads"]}, "filename": {"type": "string"}}, "required": ["location", "filename"]}}},
]


class JarvisAgent:
    def __init__(self, settings: dict[str, Any], approval: Callable[[str, str], bool]) -> None:
        self.settings = settings
        self.approval = approval
        self.history: list[dict[str, Any]] = []

    def update_settings(self, settings: dict[str, Any]) -> None:
        self.settings = settings

    def respond(
        self,
        user_text: str,
        cancel_event: threading.Event | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> str:
        """Answer a user request; cancellation is cooperative between blocking operations."""
        def cancelled() -> bool:
            return cancel_event is not None and cancel_event.is_set()

        def report(step: str) -> None:
            if progress is not None:
                try:
                    progress(step)
                except Exception:
                    # Progress/history UI must never break the actual assistant workflow.
                    pass

        if cancelled():
            return "কাজটি বাতিল করা হয়েছে। বাতিলের অনুরোধ পাওয়ার পর নতুন কোনো action শুরু করা হয়নি।"

        report("Checking supported local commands")
        direct = automation.direct_command(user_text)
        if direct is not None:
            if cancelled():
                return "বাতিলের অনুরোধ local command চলার সময় এসেছে। Command-এর ফল ইতিমধ্যে ঘটতে পারে: " + direct
            return direct
        if cancelled():
            return "কাজটি বাতিল করা হয়েছে। কোনো নতুন AI tool action চালানো হয়নি।"

        base_url = str(self.settings.get("api_base_url", "")).strip().rstrip("/")
        model = str(self.settings.get("model", "")).strip()
        if not base_url or not model:
            return "AI model সেট করা নেই। Settings-এ API endpoint ও model দিন, অথবা local AI চাইলে Ollama ইনস্টল করে সেটি চালু করুন। সাধারণ app/website কমান্ড API ছাড়াও কাজ করবে।"

        key = get_api_key()
        is_local = any(host in base_url.lower() for host in ("localhost", "127.0.0.1", "::1"))
        if not is_local and not key:
            return "AI API key পাওয়া যায়নি। Settings খুলে provider-এর API key দিন। Local Ollama ব্যবহার করলে API key ফাঁকা রাখা যাবে।"

        self.history.append({"role": "user", "content": user_text})
        self.history = self.history[-18:]
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        url = base_url + "/chat/completions"
        max_rounds = 8
        max_tool_calls = 12
        tool_call_count = 0
        try:
            for turn in range(max_rounds):
                if cancelled():
                    return "কাজটি বাতিল করা হয়েছে। আর কোনো tool action চালানো হবে না।"
                report(f"Contacting AI model (turn {turn + 1}/{max_rounds})")
                response = requests.post(
                    url,
                    headers=headers,
                    json={"model": model, "messages": messages, "tools": TOOLS, "tool_choice": "auto", "temperature": 0.4},
                    timeout=(10, 45),
                )
                # requests cannot interrupt an already-blocked network read; after it
                # returns, cancellation is checked before any model-requested tool runs.
                if cancelled():
                    return "কাজ বাতিলের অনুরোধ গৃহীত হয়েছে। বর্তমান AI request শেষ হওয়ার পরে কোনো নতুন tool action চালানো হয়নি।"
                if response.status_code >= 400:
                    details = response.text[:500]
                    if response.status_code in (401, 403):
                        return "AI provider authentication failed. Settings-এ API key এবং endpoint যাচাই করো।"
                    return f"AI provider error ({response.status_code}): {details}"
                payload = response.json()
                choices = payload.get("choices", [])
                if not choices:
                    return "AI provider কোনো উত্তর দেয়নি। Model/endpoint Settings-এ যাচাই করো।"
                message = choices[0].get("message", {})
                tool_calls = message.get("tool_calls") or []
                messages.append(message)
                if not tool_calls:
                    answer = message.get("content") or "আমি উত্তর তৈরি করতে পারিনি। আরেকবার বলো।"
                    self.history.append({"role": "assistant", "content": answer})
                    return answer
                for call in tool_calls:
                    if cancelled():
                        return "কাজটি বাতিল করা হয়েছে। বাতিলের পরে আর কোনো নতুন tool action চালানো হয়নি।"
                    if tool_call_count >= max_tool_calls:
                        report("Task action budget reached; no further tools will start")
                        return (
                            "Partially completed: নিরাপত্তার জন্য এই task-এ ১২টি tool action-এর সীমা পৌঁছেছে। "
                            "যে ফলাফলগুলো পাওয়া গেছে তা যাচাই করো, তারপর বাকি কাজের জন্য নতুন নির্দেশনা দাও।"
                        )
                    tool_call_count += 1
                    function = call.get("function", {})
                    name = function.get("name", "")
                    raw_args = function.get("arguments", "{}")
                    report(f"Running tool: {name or 'unknown'}")
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                        result = self._execute_tool(name, args)
                    except Exception as exc:
                        result = f"Tool failed safely: {type(exc).__name__}: {exc}"
                    messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "name": name, "content": str(result)[:12000]})
                    # Persist a brief, useful outcome line without copying full file contents.
                    outcome = str(result).splitlines()[0][:150] if str(result).splitlines() else "No result text"
                    report(f"Tool result: {name or 'unknown'} — {outcome}")
                    if cancelled():
                        return "কাজটি বাতিল করা হয়েছে। বর্তমানে চলমান action ফিরিয়ে নেওয়া যায় না, তবে এরপর আর কোনো tool action শুরু করা হয়নি।"
            return "Partially completed: এই task-এ ৮টি AI action round-এর সীমা পৌঁছেছে। Task History ও progress দেখো; বাকি কাজ নতুন নির্দেশনায় চালাও।"
        except requests.exceptions.ConnectionError:
            return "AI model-এ সংযোগ করা যাচ্ছে না। Local Ollama ব্যবহার করলে Ollama চালু আছে কি না ও model pull করা হয়েছে কি না দেখো; cloud provider হলে internet, endpoint ও API key যাচাই করো।"
        except requests.exceptions.Timeout:
            return "AI model উত্তর দিতে বেশি সময় নিয়েছে। আবার চেষ্টা করো অথবা ছোট নির্দেশনা দাও।"
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            return f"AI request ব্যর্থ হয়েছে: {type(exc).__name__}: {exc}"

    def _execute_tool(self, name: str, args: dict[str, Any]) -> str:
        if name == "open_application":
            return automation.open_application(str(args.get("app_name", "")))
        if name == "open_website":
            return automation.open_website(str(args.get("url_or_query", "")))
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
        if name == "create_text_file":
            return automation.create_text_file(str(args.get("location", "")), str(args.get("filename", "")), str(args.get("content", "")), self.approval)
        if name == "read_text_file":
            return automation.read_text_file(str(args.get("location", "")), str(args.get("filename", "")))
        if name == "search_file_contents":
            return automation.search_file_contents(
                str(args.get("query", "")),
                str(args.get("location", "All")),
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
