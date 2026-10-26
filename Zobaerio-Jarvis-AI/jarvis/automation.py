from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import uuid
import webbrowser
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

def _known_user_folder(display_name: str) -> Path:
    """Resolve Windows shell folders (including OneDrive redirection) when possible."""
    if os.name == "nt":
        try:
            import winreg
            registry_names = {
                "Desktop": "Desktop",
                "Documents": "Personal",
                "Downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
            }
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                value, _ = winreg.QueryValueEx(key, registry_names[display_name])
                resolved = Path(os.path.expandvars(value)).expanduser()
                if resolved.exists():
                    return resolved
        except (OSError, ImportError, KeyError):
            pass
    home = Path.home()
    one_drive = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer") or os.environ.get("OneDriveCommercial")
    candidates = []
    if one_drive:
        candidates.append(Path(one_drive) / display_name)
    candidates.extend([home / display_name, home / "OneDrive" / display_name])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return home / display_name


ROOTS = {
    "desktop": _known_user_folder("Desktop"),
    "documents": _known_user_folder("Documents"),
    "downloads": _known_user_folder("Downloads"),
}

APP_ALIASES = {
    "notepad": ["notepad"], "নোটপ্যাড": ["notepad"],
    "calculator": ["calc"], "ক্যালকুলেটর": ["calc"], "calc": ["calc"],
    "paint": ["mspaint"], "পেইন্ট": ["mspaint"],
    "file explorer": ["explorer"], "explorer": ["explorer"], "ফাইল এক্সপ্লোরার": ["explorer"],
    "task manager": ["taskmgr"], "taskmgr": ["taskmgr"],
    "word": ["winword"], "microsoft word": ["winword"],
    "excel": ["excel"], "microsoft excel": ["excel"],
    "powerpoint": ["powerpnt"], "microsoft powerpoint": ["powerpnt"], "power point": ["powerpnt"],
    "outlook": ["outlook"], "microsoft outlook": ["outlook"],
    "onenote": ["onenote"], "one note": ["onenote"],
    "snipping tool": ["SnippingTool.exe"], "snippingtool": ["SnippingTool.exe"],
    "vscode": ["code"], "vs code": ["code"], "visual studio code": ["code"],
}


def normalize_location(location: str) -> Path:
    key = location.strip().lower().replace(" ", "")
    aliases = {"ডেস্কটপ": "desktop", "ডকুমেন্টস": "documents", "documents": "documents",
               "ডাউনলোডস": "downloads", "download": "downloads", "ডাউনলোড": "downloads"}
    key = aliases.get(key, key)
    if key not in ROOTS:
        raise ValueError("Location must be Desktop, Documents, or Downloads.")
    path = ROOTS[key]
    path.mkdir(parents=True, exist_ok=True)
    return path


def _known_executable(executable: str) -> Path | None:
    """Find common Windows applications outside PATH (especially Office)."""
    direct = shutil.which(executable)
    if direct:
        return Path(direct)
    if os.name != "nt":
        return None
    roots = []
    for env_name in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "LOCALAPPDATA"):
        value = os.environ.get(env_name)
        if value:
            roots.append(Path(value))
    candidates: list[Path] = []
    lowered = executable.lower()
    if lowered in {"winword", "winword.exe", "excel", "excel.exe", "powerpnt", "powerpnt.exe", "outlook", "outlook.exe", "onenote", "onenote.exe"}:
        filename = executable if executable.lower().endswith(".exe") else executable + ".EXE"
        for root in roots:
            for office in ("Microsoft Office/root/Office16", "Microsoft Office/Office16", "Microsoft Office/root/Office15", "Microsoft Office/Office15"):
                candidates.append(root / office / filename)
    elif lowered in {"chrome", "chrome.exe"}:
        for root in roots:
            candidates.extend([root / "Google/Chrome/Application/chrome.exe"])
    elif lowered in {"msedge", "msedge.exe", "edge"}:
        for root in roots:
            candidates.append(root / "Microsoft/Edge/Application/msedge.exe")
    elif lowered in {"snippingtool", "snippingtool.exe"}:
        windir = os.environ.get("WINDIR", r"C:\Windows")
        candidates.append(Path(windir) / "System32" / "SnippingTool.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def open_application(app_name: str) -> str:
    key = app_name.strip().lower()
    if key in {"browser", "web browser"}:
        webbrowser.open("https://www.google.com")
        return "Default web browser opened."
    if key in {"chrome", "google chrome"}:
        executable = _known_executable("chrome.exe")
        if executable:
            subprocess.Popen([str(executable), "https://www.google.com"], shell=False)
            return "Google Chrome opened."
        webbrowser.open("https://www.google.com")
        return "Google Chrome was not found; the default web browser was opened instead."
    if key in {"edge", "microsoft edge"}:
        executable = _known_executable("msedge.exe")
        if executable:
            subprocess.Popen([str(executable), "https://www.google.com"], shell=False)
            return "Microsoft Edge opened."
        webbrowser.open("https://www.google.com")
        return "Microsoft Edge was not found; the default web browser was opened instead."
    if key in {"settings", "windows settings", "সেটিংস"}:
        if os.name == "nt":
            os.startfile("ms-settings:")  # type: ignore[attr-defined]
            return "Windows Settings opened."
        return "Windows Settings can only be opened on Windows."
    command = APP_ALIASES.get(key)
    if not command:
        allowed = ", ".join(sorted(set(APP_ALIASES) | {"browser", "settings", "chrome", "edge"}))
        return f"I can open these supported apps: {allowed}."
    try:
        executable = _known_executable(command[0])
        actual_command = [str(executable)] + command[1:] if executable else command
        subprocess.Popen(actual_command, shell=False)
        return f"Opened {app_name}."
    except FileNotFoundError:
        if key in {"vscode", "vs code", "visual studio code"}:
            return "VS Code command was not found. Install Visual Studio Code or enable its 'code' command."
        if key in {"word", "microsoft word", "excel", "microsoft excel", "powerpoint", "power point", "microsoft powerpoint", "outlook", "microsoft outlook", "onenote", "one note"}:
            return f"Microsoft Office app '{app_name}' was not found. Check that it is installed."
        return f"Windows could not find the app '{app_name}'."


SOCIAL_WEBSITE_ALIASES = {
    "whatsapp": "https://web.whatsapp.com/",
    "واتসঅ্যাপ": "https://web.whatsapp.com/",
    "হোয়াটসঅ্যাপ": "https://web.whatsapp.com/",
    "হোয়াটসঅ্যাপ": "https://web.whatsapp.com/",
    "facebook": "https://www.facebook.com/",
    "ফেসবুক": "https://www.facebook.com/",
    "youtube": "https://www.youtube.com/",
    "ইউটিউব": "https://www.youtube.com/",
    "instagram": "https://www.instagram.com/",
    "ইনস্টাগ্রাম": "https://www.instagram.com/",
    "messenger": "https://www.messenger.com/",
    "মেসেঞ্জার": "https://www.messenger.com/",
}

WORKSPACE_WEBSITE_ALIASES = {
    "gmail": "https://mail.google.com/",
    "google mail": "https://mail.google.com/",
    "জিমেইল": "https://mail.google.com/",
    "google calendar": "https://calendar.google.com/",
    "calendar": "https://calendar.google.com/",
    "ক্যালেন্ডার": "https://calendar.google.com/",
    "google drive": "https://drive.google.com/",
    "drive": "https://drive.google.com/",
    "গুগল ড্রাইভ": "https://drive.google.com/",
    "google docs": "https://docs.google.com/",
    "docs": "https://docs.google.com/",
    "গুগল ডকস": "https://docs.google.com/",
    "google sheets": "https://sheets.google.com/",
    "sheets": "https://sheets.google.com/",
    "google maps": "https://maps.google.com/",
    "maps": "https://maps.google.com/",
    "গুগল ম্যাপস": "https://maps.google.com/",
}



def _youtube_search_query(value: str) -> str | None:
    """Extract an explicit YouTube search request in English or Bangla."""
    patterns = (
        r"^(?:search|find)\s+(?:on\s+)?youtube\s+(?:for\s+)?(.+)$",
        r"^youtube\s+(?:search|find)\s+(?:for\s+)?(.+)$",
        r"^ইউটিউবে\s+(.+?)(?:\s+(?:সার্চ|খুঁজে)(?:\s+করো|\s+দাও)?)?$",
        r"^ইউটিউব\s+(?:এ|তে)\s+(.+?)(?:\s+(?:সার্চ|খুঁজে)(?:\s+করো|\s+দাও)?)?$",
    )
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            query = match.group(1).strip(" \\t।.!?")
            if query and query.casefold() not in {"open", "খোলো", "চালু করো"}:
                return query
    return None


def open_website(url_or_query: str) -> str:
    value = url_or_query.strip()
    if not value:
        return "Tell me a website or something to search for."

    # Explicit video searches should land on YouTube results, not generic Google results.
    video_query = _youtube_search_query(value)
    if video_query:
        url = "https://www.youtube.com/results?search_query=" + quote(video_query)
        webbrowser.open(url)
        return f"Searched YouTube for: {video_query}."

    known_site = SOCIAL_WEBSITE_ALIASES.get(value.casefold())
    if known_site:
        webbrowser.open(known_site)
        return f"Opened {known_site}."
    workspace_site = WORKSPACE_WEBSITE_ALIASES.get(value.casefold())
    if workspace_site:
        webbrowser.open(workspace_site)
        return f"Opened {workspace_site}."

    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        webbrowser.open(value)
        return f"Opened {value}."
    if "." in value and " " not in value:
        candidate = "https://" + value
        parsed = urlparse(candidate)
        if parsed.netloc and "." in parsed.netloc:
            webbrowser.open(candidate)
            return f"Opened {candidate}."
    url = "https://www.google.com/search?q=" + quote(value)
    webbrowser.open(url)
    return f"Searched the web for: {value}."



def prepare_whatsapp_message(phone_number: str, message: str) -> str:
    """Open WhatsApp Web with a validated recipient and prefilled draft; never send it."""
    raw_phone = str(phone_number).strip()
    digits = re.sub(r"[\s()+.-]", "", raw_phone)
    # Accept ASCII international phone digits only; str.isdigit() also accepts Unicode numerals.
    if re.fullmatch(r"[0-9]{8,15}", digits) is None:
        return "WhatsApp draft blocked: provide an international phone number with 8–15 digits, including country code (for example, +8801XXXXXXXXX)."
    text = str(message).strip()
    if not text:
        return "WhatsApp draft not opened: message text is empty."
    if len(text) > 4000:
        return "WhatsApp draft blocked: message must be 4,000 characters or fewer."
    if any(ord(char) < 32 and char not in "\n\r\t" for char in text):
        return "WhatsApp draft blocked: message contains unsupported control characters."
    url = "https://web.whatsapp.com/send?phone=" + digits + "&text=" + quote(text, safe="")
    webbrowser.open(url)
    return (
        "Opened WhatsApp Web with a prefilled message draft for the supplied number. "
        "Nothing was sent. Review the recipient and message in WhatsApp, then click Send yourself."
    )



def prepare_calendar_event_draft(title: str, start: str, end: str, details: str = "", location: str = "", timezone_name: str = "Asia/Dhaka") -> str:
    """Open a Google Calendar event template; never create or save the event automatically."""
    from datetime import datetime
    from urllib.parse import urlencode

    title_text = str(title).strip()
    if not title_text or len(title_text) > 200:
        return "Calendar draft blocked: event title must be 1–200 characters."
    if any(ord(char) < 32 for char in title_text):
        return "Calendar draft blocked: title contains unsupported control characters."

    def parse_local(value: str, label: str) -> datetime | None:
        raw = str(value).strip()
        try:
            parsed = datetime.fromisoformat(raw)
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed.tzinfo is not None:
            return None
        if not raw or parsed.second != 0 or parsed.microsecond != 0:
            return None
        return parsed

    start_dt = parse_local(start, "start")
    end_dt = parse_local(end, "end")
    if start_dt is None or end_dt is None:
        return "Calendar draft blocked: start and end must be local ISO dates/times like 2026-10-26T14:30, without a timezone offset."
    if end_dt <= start_dt:
        return "Calendar draft blocked: end time must be after start time."
    if (end_dt - start_dt).total_seconds() > 7 * 24 * 60 * 60:
        return "Calendar draft blocked: event duration cannot exceed 7 days."
    details_text, location_text = str(details).strip(), str(location).strip()
    if len(details_text) > 4000 or len(location_text) > 300:
        return "Calendar draft blocked: details must be 4,000 characters or fewer and location 300 or fewer."
    if any(ord(char) < 32 and char not in "\n\r\t" for char in details_text) or any(ord(char) < 32 for char in location_text):
        return "Calendar draft blocked: details or location contain unsupported control characters."
    if timezone_name not in {"Asia/Dhaka", "UTC", "Asia/Kolkata", "Asia/Singapore", "Europe/London", "America/New_York", "America/Los_Angeles"}:
        return "Calendar draft blocked: timezone is not in the supported allow-list."
    dates = start_dt.strftime("%Y%m%dT%H%M%S") + "/" + end_dt.strftime("%Y%m%dT%H%M%S")
    params = {"action": "TEMPLATE", "text": title_text, "dates": dates, "ctz": timezone_name}
    if details_text:
        params["details"] = details_text
    if location_text:
        params["location"] = location_text
    url = "https://calendar.google.com/calendar/render?" + urlencode(params)
    webbrowser.open(url)
    return "Opened a Google Calendar event draft. Nothing was saved or invited automatically. Review the title, time, timezone, details and location, then save it yourself."


def prepare_email_draft(recipient: str, subject: str, body: str) -> str:
    """Open the default email app with a validated mailto draft; never send it."""
    address = str(recipient).strip()
    # Keep this deliberately conservative: one address only, no display names or header syntax.
    if len(address) > 254 or re.fullmatch(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.[A-Za-z]{2,}",
        address,
    ) is None:
        return "Email draft blocked: provide one valid recipient email address."
    subject_text = str(subject).strip()
    body_text = str(body).strip()
    if len(subject_text) > 200:
        return "Email draft blocked: subject must be 200 characters or fewer."
    if any(ord(char) < 32 and char not in "\t" for char in subject_text):
        return "Email draft blocked: subject contains unsupported control characters."
    if not body_text:
        return "Email draft not opened: email body is empty."
    if len(body_text) > 5000:
        return "Email draft blocked: body must be 5,000 characters or fewer."
    if any(ord(char) < 32 and char not in "\n\r\t" for char in body_text):
        return "Email draft blocked: body contains unsupported control characters."
    url = "mailto:" + quote(address, safe="@.+_%-")
    params = []
    if subject_text:
        params.append("subject=" + quote(subject_text, safe=""))
    params.append("body=" + quote(body_text, safe=""))
    url += "?" + "&".join(params)
    webbrowser.open(url)
    return (
        "Opened the default email app with a draft addressed to the supplied recipient. "
        "Nothing was sent. Review the recipient, subject and message, then send it yourself."
    )



def open_folder(location: str) -> str:
    path = normalize_location(location)
    os.startfile(str(path))  # type: ignore[attr-defined]
    return f"Opened {path}."


def search_files(query: str) -> str:
    needle = query.strip().casefold()
    if not needle:
        return "Tell me the file or folder name to search for."
    results: list[str] = []
    scanned = 0
    for root in ROOTS.values():
        if not root.exists():
            continue
        for current, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"node_modules", ".git", "__pycache__"}]
            for name in dirs + files:
                scanned += 1
                if needle in name.casefold():
                    results.append(str(Path(current) / name))
                    if len(results) >= 20:
                        break
                if scanned >= 12000 or len(results) >= 20:
                    break
            if scanned >= 12000 or len(results) >= 20:
                break
        if scanned >= 12000 or len(results) >= 20:
            break
    if not results:
        return "No matching files or folders were found in Desktop, Documents, or Downloads."
    return "Matching items:\n" + "\n".join(f"• {p}" for p in results)



CONTENT_SEARCH_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".log", ".yaml", ".yml", ".xml", ".ini", ".toml",
    ".html", ".htm", ".css", ".js", ".ts", ".tsx", ".jsx", ".py", ".sql", ".java",
    ".c", ".h", ".cpp", ".go", ".rs", ".php", ".rb", ".swift", ".kt", ".vue", ".svelte",
}
MAX_CONTENT_SEARCH_FILES = 5000
MAX_CONTENT_SEARCH_FILE_BYTES = 256_000
MAX_CONTENT_SEARCH_MATCHES = 20
CONTENT_SEARCH_IGNORED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "AppData",
    "System Volume Information", "$Recycle.Bin", ".cache",
}


def search_file_contents(query: str, location: str, approve) -> str:
    """Search bounded text snippets in approved user folders, only after explicit consent."""
    term = str(query).strip()
    if len(term) < 2:
        return "Give me a search phrase with at least 2 characters."
    if len(term) > 120 or any(ord(char) < 32 and char not in "\t" for char in term):
        return "Search phrase must be 2–120 characters and cannot contain control characters."

    label = str(location).strip()
    if label.casefold() == "all":
        selected_roots = [
            ("Desktop", ROOTS["desktop"]),
            ("Documents", ROOTS["documents"]),
            ("Downloads", ROOTS["downloads"]),
        ]
    else:
        aliases = {
            "desktop": "desktop", "documents": "documents", "downloads": "downloads",
            "ডেস্কটপ": "desktop", "ডকুমেন্টস": "documents", "ডাউনলোডস": "downloads",
        }
        key = aliases.get(label.casefold())
        if key is None:
            return "Location must be Desktop, Documents, Downloads, or All."
        selected_roots = [(label.title(), ROOTS[key])]

    scope_names = ", ".join(name for name, _root in selected_roots)
    details = (
        f"Search for this text: {term}\n"
        f"Folders: {scope_names}\n\n"
        f"J.A.R.V.I.S will inspect only common text/source files, skip files larger than "
        f"{MAX_CONTENT_SEARCH_FILE_BYTES:,} bytes, scan at most {MAX_CONTENT_SEARCH_FILES:,} files, "
        f"and return at most {MAX_CONTENT_SEARCH_MATCHES} short matching-line excerpts. "
        "Matching excerpts will be sent into the current AI conversation and may be sent to the configured AI provider. "
        "No files will be edited. Approve this local content search?"
    )
    try:
        if not approve("Confirm local content search", details):
            return "Cancelled. No file contents were searched."
    except Exception as exc:
        return f"Could not obtain approval ({type(exc).__name__}). No files were searched."

    needle = term.casefold()
    matches: list[str] = []
    scanned = 0
    skipped_large = 0
    scan_limit_hit = False
    match_limit_hit = False
    stop = False
    ignored_names = {name.casefold() for name in CONTENT_SEARCH_IGNORED_DIRS}

    for root_label, root in selected_roots:
        if stop or not root.exists():
            continue
        try:
            root_resolved = root.resolve()
        except OSError:
            continue
        for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
            current_path = Path(current)
            directories[:] = [
                name for name in directories
                if not name.startswith(".")
                and name.casefold() not in ignored_names
                and not (current_path / name).is_symlink()
            ]
            for filename in filenames:
                if scanned >= MAX_CONTENT_SEARCH_FILES:
                    scan_limit_hit = True
                    stop = True
                    break
                scanned += 1
                path = current_path / filename
                if path.is_symlink() or path.suffix.casefold() not in CONTENT_SEARCH_EXTENSIONS:
                    continue
                try:
                    resolved = path.resolve(strict=True)
                    if not resolved.is_relative_to(root_resolved):
                        continue
                    if not path.is_file():
                        continue
                    metadata = path.stat()
                    if metadata.st_size > MAX_CONTENT_SEARCH_FILE_BYTES:
                        skipped_large += 1
                        continue
                    with path.open("rb") as stream:
                        raw = stream.read(MAX_CONTENT_SEARCH_FILE_BYTES + 1)
                    if len(raw) > MAX_CONTENT_SEARCH_FILE_BYTES or b"\x00" in raw:
                        skipped_large += 1
                        continue
                    text_content = raw.decode("utf-8", errors="replace")
                except OSError:
                    continue

                for line_number, line in enumerate(text_content.splitlines(), start=1):
                    if needle not in line.casefold():
                        continue
                    snippet = line.strip()
                    if len(snippet) > 220:
                        snippet = snippet[:217] + "..."
                    matches.append(f"{path} (line {line_number}): {snippet}")
                    if len(matches) >= MAX_CONTENT_SEARCH_MATCHES:
                        match_limit_hit = True
                        stop = True
                        break
                if stop:
                    break
            if stop:
                break

    if not matches:
        summary = f"No matching lines found in {scope_names}. Scanned {scanned:,} file(s)."
    else:
        summary = f"Found {len(matches)} matching line(s) in {scope_names} after scanning {scanned:,} file(s):\n"
        summary += "\n".join(f"- {item}" for item in matches)
    notes = []
    if skipped_large:
        notes.append(f"skipped {skipped_large:,} large/binary file(s)")
    if scan_limit_hit:
        notes.append(f"stopped at the {MAX_CONTENT_SEARCH_FILES:,}-file scan limit")
    if match_limit_hit:
        notes.append(f"returned only the first {MAX_CONTENT_SEARCH_MATCHES} matching lines")
    if notes:
        summary += "\n\nSearch limits: " + "; ".join(notes) + "."
    return summary


def get_system_info() -> str:
    return (
        f"Operating system: {platform.system()} {platform.release()}\n"
        f"Computer: {platform.node()}\n"
        f"Python: {platform.python_version()}\n"
        f"Current time: {datetime.now().astimezone().strftime('%Y-%m-%d %I:%M:%S %p %Z')}"
    )


WINDOW_SHORTCUTS: dict[str, tuple[str, ...]] = {
    "CTRL+S": ("ctrl", "s"),
    "CTRL+A": ("ctrl", "a"),
    "CTRL+C": ("ctrl", "c"),
    "CTRL+V": ("ctrl", "v"),
    "CTRL+Z": ("ctrl", "z"),
    "CTRL+Y": ("ctrl", "y"),
    "CTRL+F": ("ctrl", "f"),
    "TAB": ("tab",),
    "SHIFT+TAB": ("shift", "tab"),
    "ESC": ("esc",),
    "HOME": ("home",),
    "END": ("end",),
    "PAGEUP": ("pageup",),
    "PAGEDOWN": ("pagedown",),
}


def normalize_allowed_shortcut(shortcut: str) -> tuple[str, ...]:
    """Return a mapped keystroke sequence; never pass arbitrary keys to the OS."""
    key = "+".join(part.strip().upper() for part in str(shortcut).split("+") if part.strip())
    if key not in WINDOW_SHORTCUTS:
        raise ValueError(
            "Shortcut is not allow-listed. Supported shortcuts: "
            + ", ".join(WINDOW_SHORTCUTS)
            + ". Enter, Alt+F4, Windows+R and arbitrary key sequences are blocked."
        )
    return WINDOW_SHORTCUTS[key]


def _windows_api():
    if os.name != "nt":
        raise OSError("Foreground-window automation is supported only on Windows.")
    import ctypes

    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
    user32.IsWindowVisible.restype = ctypes.c_bool
    user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    user32.SetForegroundWindow.restype = ctypes.c_bool
    return ctypes, user32


def _window_title(user32, hwnd) -> str:
    length = int(user32.GetWindowTextLengthW(hwnd))
    if length <= 0:
        return ""
    import ctypes

    buffer = ctypes.create_unicode_buffer(min(length + 1, 1024))
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value.strip()


def _enumerate_windows() -> list[tuple[object, str]]:
    ctypes, user32 = _windows_api()
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    found: list[tuple[object, str]] = []

    @callback_type
    def callback(hwnd, _lparam) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        title = _window_title(user32, hwnd)
        if title:
            found.append((hwnd, title[:240]))
        return True

    user32.EnumWindows.argtypes = [callback_type, ctypes.c_void_p]
    user32.EnumWindows.restype = ctypes.c_bool
    user32.EnumWindows(callback, 0)
    return found


def list_open_windows() -> str:
    """List titles of visible top-level windows; does not capture their contents."""
    if os.name != "nt":
        return "Listing desktop windows is supported only on Windows."
    try:
        rows = _enumerate_windows()
    except Exception as exc:
        return f"Could not list visible windows: {type(exc).__name__}: {exc}"
    if not rows:
        return "No titled application windows were found."
    titles = list(dict.fromkeys(title for _hwnd, title in rows))
    return "Visible window titles (titles only; no screen contents captured):\n" + "\n".join(
        f"- {title}" for title in titles[:30]
    )


def get_active_window_title() -> str:
    """Return the foreground application's title only, without reading its content."""
    if os.name != "nt":
        return "Active-window titles are supported only on Windows."
    try:
        _ctypes, user32 = _windows_api()
        title = _window_title(user32, user32.GetForegroundWindow())
        return f"Active window title: {title}" if title else "The active window has no readable title."
    except Exception as exc:
        return f"Could not read active window title: {type(exc).__name__}: {exc}"


def _find_window(expected_app: str, timeout: float = 0.0):
    target = expected_app.strip()
    if not target or len(target) > 100 or any(ch in target for ch in "\r\n\x00"):
        raise ValueError("Provide a short application/window-title fragment.")
    deadline = __import__("time").monotonic() + max(0.0, min(timeout, 5.0))
    while True:
        for hwnd, title in _enumerate_windows():
            if target.casefold() in title.casefold():
                return hwnd, title
        if __import__("time").monotonic() >= deadline:
            return None
        __import__("time").sleep(0.15)


def _activate_window(expected_app: str):
    _ctypes, user32 = _windows_api()
    result = _find_window(expected_app, timeout=0.8)
    if result is None:
        return None
    hwnd, title = result
    # SW_RESTORE also brings minimized target apps back to a usable state.
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    import time

    deadline = time.monotonic() + 1.2
    while time.monotonic() < deadline:
        if user32.GetForegroundWindow() == hwnd:
            return hwnd, title
        time.sleep(0.05)
    return None


def paste_text_into_window(text: str, expected_app: str, approve) -> str:
    """Paste user-approved text into a specific visible Windows window title."""
    if os.name != "nt":
        return "Typing into other applications is supported only on Windows."
    value = str(text)
    if not value.strip():
        return "There is no text to paste."
    if len(value) > 8000:
        return "For safety, a single paste is limited to 8,000 characters."
    try:
        found = _find_window(expected_app, timeout=1.0)
    except (OSError, ValueError) as exc:
        return str(exc)
    if found is None:
        return f"No visible window title matched '{expected_app}'. Nothing was typed."
    _hwnd, title = found
    preview = value[:1200] + ("… [preview truncated]" if len(value) > 1200 else "")
    detail = (
        f"Target window: {title}\n\n"
        f"Paste {len(value)} character(s) into the target application's current field?\n"
        "This action does not press Enter or submit a form. Verify the target and text before approving.\n\n"
        f"Text preview:\n{preview}"
    )
    if not approve("Confirm text entry", detail):
        return "Cancelled. No text was pasted."
    try:
        activated = _activate_window(expected_app)
        if activated is None:
            return f"Could not bring '{title}' to the foreground after approval. Nothing was pasted."
        import pyautogui
        import pyperclip

        previous_clipboard = None
        try:
            previous_clipboard = pyperclip.paste()
        except Exception:
            pass
        try:
            pyperclip.copy(value)
            pyautogui.hotkey("ctrl", "v")
            __import__("time").sleep(0.2)
        finally:
            if previous_clipboard is not None:
                try:
                    pyperclip.copy(previous_clipboard)
                except Exception:
                    pass
        return (
            f"Paste keystroke sent to '{activated[1]}' for {len(value)} character(s). "
            "Check the target field visually; this feature does not independently verify the final document contents."
        )
    except Exception as exc:
        return f"Text entry failed safely: {type(exc).__name__}: {exc}"


def press_allowed_shortcut(shortcut: str, expected_app: str, approve) -> str:
    """Send one allow-listed editing/navigation shortcut after explicit approval."""
    try:
        keys = normalize_allowed_shortcut(shortcut)
    except ValueError as exc:
        return str(exc)
    if os.name != "nt":
        return "Foreground-window shortcut automation is supported only on Windows."
    try:
        found = _find_window(expected_app, timeout=1.0)
    except (OSError, ValueError) as exc:
        return str(exc)
    if found is None:
        return f"No visible window title matched '{expected_app}'. No shortcut was sent."
    _hwnd, title = found
    key_label = "+".join(keys).upper()
    if not approve(
        "Confirm keyboard shortcut",
        f"Target window: {title}\n\nSend shortcut {key_label}?\n\n"
        "This can change the active document or app state. Shortcuts that submit forms, close windows, or launch system commands are not allow-listed.",
    ):
        return "Cancelled. No shortcut was sent."
    try:
        activated = _activate_window(expected_app)
        if activated is None:
            return f"Could not bring '{title}' to the foreground after approval. No shortcut was sent."
        import pyautogui

        pyautogui.hotkey(*keys) if len(keys) > 1 else pyautogui.press(keys[0])
        return f"Sent allow-listed shortcut {key_label} to '{activated[1]}'. Verify the resulting state in that app."
    except Exception as exc:
        return f"Shortcut failed safely: {type(exc).__name__}: {exc}"


def safe_child_path(location: str, name: str) -> Path:
    base = normalize_location(location)
    raw = name.strip()
    if not raw or raw in {".", ".."} or Path(raw).name != raw or any(c in raw for c in '<>:"/\\|?*'):
        raise ValueError("Use a simple file/folder name without a path or reserved characters.")
    path = (base / raw).resolve()
    if base.resolve() not in path.parents:
        raise ValueError("That path is outside the allowed folder.")
    return path


def verify_local_action(kind: str, target: str, location: str = "Desktop") -> str:
    """Verify a visible window title or a safe relative file/folder path in an allowed user folder."""
    action = str(kind).strip().casefold()
    needle = str(target).strip()
    if not needle:
        return "Verification needs a target name."
    if action == "window":
        if os.name != "nt":
            return "Visible-window verification is supported only on Windows."
        try:
            match = _find_window(needle, timeout=2.0)
        except (OSError, ValueError) as exc:
            return f"Window verification failed: {exc}"
        if match is None:
            return f"Not verified: no visible application window title matched '{needle}'."
        return f"Verified: visible application window title is '{match[1]}'."
    if action not in {"file", "folder"}:
        return "Verification kind must be window, file, or folder."
    try:
        # Use the same no-symlink, no-traversal containment checks as approved nested
        # file creation so valid Project/report.txt targets can be verified as well.
        path = _safe_nested_file_path(location, needle)
    except (ValueError, OSError) as exc:
        return f"Verification blocked: {exc}"
    if action == "file":
        try:
            if path.is_file() and not path.is_symlink():
                return f"Verified file exists: {path} ({path.stat().st_size} bytes)."
        except OSError:
            return f"Verification failed while inspecting the file at {path}."
        return f"Not verified: no file exists at {path}."
    try:
        if path.is_dir() and not path.is_symlink():
            return f"Verified folder exists: {path}."
    except OSError:
        return f"Verification failed while inspecting the folder at {path}."
    return f"Not verified: no folder exists at {path}."


def create_folder(location: str, name: str, approve) -> str:
    path = safe_child_path(location, name)
    if path.exists():
        return f"A folder or file already exists at {path}. Nothing was changed."
    if not approve("Create folder", f"Create this folder?\n\n{path}"):
        return "Cancelled. No folder was created."
    path.mkdir(parents=False, exist_ok=False)
    return f"Created folder: {path}"


def create_folder_structure(location: str, folder_paths: list[str], approve) -> str:
    """Create a bounded nested folder structure after one explicit approval, without overwriting."""
    if not isinstance(folder_paths, list) or not 1 <= len(folder_paths) <= 30:
        return "Folder structure blocked: provide between 1 and 30 relative folder paths."
    try:
        root = normalize_location(location)
    except (ValueError, OSError) as exc:
        return f"Folder structure blocked: {exc}"

    planned: dict[str, Path] = {}
    for raw in folder_paths:
        if not isinstance(raw, str):
            return "Folder structure blocked: every path must be text."
        value = raw.strip()
        parts = value.replace("\\", "/").split("/")
        if not value or len(parts) > 8 or any(
            not part or part in {".", ".."} or part != part.strip()
            or any(c in part for c in '<>:"|?*')
            or any(ord(c) < 32 for c in part)
            for part in parts
        ):
            return "Folder structure blocked: use simple folder names, with at most 8 levels and no absolute paths or reserved characters."
        for index in range(1, len(parts) + 1):
            relative = "/".join(parts[:index])
            key = relative.casefold()
            candidate = root.joinpath(*parts[:index])
            # Resolve and prove containment while allowing only the validated relative segments above.
            try:
                checked = candidate.resolve(strict=False)
                if root.resolve() not in checked.parents:
                    return "Folder structure blocked: path escaped the selected folder."
            except (ValueError, OSError) as exc:
                return f"Folder structure blocked: {exc}"
            current = root
            for part in parts[:index]:
                current = current / part
                if current.is_symlink():
                    return "Folder structure blocked: symbolic links are not supported."
            planned[key] = candidate

    ordered = sorted(planned.values(), key=lambda p: (len(p.parts), str(p).casefold()))
    existing = [path for path in ordered if path.exists()]
    if existing:
        return "Folder structure not created because these destinations already exist:\n" + "\n".join(str(p) for p in existing)
    details = (
        f"Create this folder structure under {root}?\n\n"
        + "\n".join(f"• {path}" for path in ordered)
        + "\n\nAll listed folders and required parent folders will be created. Existing destinations are never overwritten. Approve?"
    )
    try:
        if not approve("Create folder structure", details):
            return "Cancelled. No folders were created."
    except Exception as exc:
        return f"Could not obtain approval ({type(exc).__name__}). No folders were created."

    # Recheck after the approval dialog; fail closed if any destination appeared.
    if any(path.exists() or path.is_symlink() for path in ordered):
        return "Folder structure changed after confirmation. No folders were created; review the destination and try again."
    created: list[Path] = []
    try:
        for path in ordered:
            path.mkdir(parents=False, exist_ok=False)
            created.append(path)
    except (OSError, FileExistsError) as exc:
        # Roll back only directories created by this call, and only if still empty.
        for path in reversed(created):
            try:
                path.rmdir()
            except OSError:
                pass
        return f"Folder structure creation stopped safely ({type(exc).__name__}); created empty folders were rolled back where possible."
    return f"Created {len(created)} folders under {root}:\n" + "\n".join(str(path) for path in created)


def _safe_nested_file_path(location: str, relative_path: str) -> Path:
    """Resolve a file path under an approved root; allow existing subfolders, never links/traversal."""
    root = normalize_location(location).resolve()
    raw = str(relative_path).strip()
    parts = raw.replace("\\", "/").split("/")
    if (
        not raw or len(parts) > 9 or raw.startswith("/") or
        any(not part or part in {".", ".."} or part != part.strip()
            or any(c in part for c in '<>:"|?*')
            or any(ord(c) < 32 for c in part) for part in parts)
    ):
        raise ValueError("Use a relative file path with simple names, no traversal or reserved characters, and at most 8 folders.")
    candidate = root.joinpath(*parts)
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Symbolic links are not supported for file creation.")
    resolved = candidate.resolve(strict=False)
    if root not in resolved.parents:
        raise ValueError("That path is outside the allowed folder.")
    if not candidate.parent.is_dir():
        raise ValueError("The parent folder must already exist. Create the folder structure first.")
    return candidate


def create_text_file(location: str, filename: str, content: str, approve) -> str:
    try:
        path = _safe_nested_file_path(location, filename)
    except (ValueError, OSError) as exc:
        return f"File creation blocked: {exc}"
    if path.suffix.lower() not in {".txt", ".md", ".csv", ".json", ".log"}:
        return "For safety, I can create .txt, .md, .csv, .json, or .log files only."
    if path.exists():
        return f"File already exists at {path}. I will not overwrite it."
    if len(content) > 100_000:
        return "The content is too long (maximum 100,000 characters)."
    try:
        if not approve("Create file", f"Create this file?\\n\\n{path}\\n\\nContent preview:\\n{content[:700]}"):
            return "Cancelled. No file was created."
    except Exception as exc:
        return f"Could not obtain approval ({type(exc).__name__}). No file was created."
    # Exclusive creation prevents overwriting a file created while approval was open.
    try:
        with path.open("x", encoding="utf-8", newline="") as stream:
            stream.write(content)
    except FileExistsError:
        return f"File already exists at {path}. I will not overwrite it."
    except OSError as exc:
        return f"File creation failed safely ({type(exc).__name__})."
    return f"Created file: {path}"


def read_text_file(location: str, filename: str, approve) -> str:
    """Read a small text file only after explicit consent; disclose AI-provider transmission."""
    allowed_suffixes = {".txt", ".md", ".csv", ".json", ".log", ".py", ".yaml", ".yml", ".xml"}
    try:
        path = _operation_child_path(location, filename)
    except (ValueError, OSError) as exc:
        return f"File read blocked: {exc}"
    if path.suffix.lower() not in allowed_suffixes:
        return "For safety, I can read common text and source-code files only."
    if not path.is_file():
        return f"File not found: {path}"
    try:
        before = path.stat()
    except OSError as exc:
        return f"Could not inspect the file before reading: {exc}"
    if before.st_size > 100_000:
        return "That file is larger than 100 KB, so I will not read it into the chat."
    detail = (
        f"Read this text file into the AI conversation?\n\n"
        f"File: {path}\n"
        f"Size: {before.st_size:,} bytes\n\n"
        "The file contents will be sent into the current AI conversation and may be sent to the configured AI provider. "
        "Review the path and avoid reading passwords, API keys, private credentials, or sensitive personal data. "
        "No changes will be made to this file. Approve reading it?"
    )
    try:
        if not approve("Confirm read file", detail):
            return "Cancelled. No file contents were read."
    except Exception as exc:
        return f"Could not obtain approval ({type(exc).__name__}). No file contents were read."

    try:
        current = _operation_child_path(location, filename)
        after_approval = current.stat()
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        identity_after = (
            after_approval.st_dev,
            after_approval.st_ino,
            after_approval.st_size,
            after_approval.st_mtime_ns,
        )
        if current != path or identity_after != identity_before:
            return "The file changed after confirmation. No contents were returned; review it and try again."
        with current.open("rb") as stream:
            opened_before = os.fstat(stream.fileno())
            opened_identity = (
                opened_before.st_dev, opened_before.st_ino, opened_before.st_size, opened_before.st_mtime_ns
            )
            if opened_identity != identity_after:
                return "The file changed after confirmation. No contents were returned; review it and try again."
            raw = stream.read(100_001)
            opened_after = os.fstat(stream.fileno())
        final_identity = (
            opened_after.st_dev, opened_after.st_ino, opened_after.st_size, opened_after.st_mtime_ns
        )
        if final_identity != opened_identity:
            return "The file changed while it was being read. No contents were returned."
        if len(raw) > 100_000:
            return "The file grew beyond 100 KB while being read, so no contents were returned."
        if b"\x00" in raw:
            return "For safety, this file appears to contain binary data and was not returned to the AI conversation."
        text_content = raw.decode("utf-8", errors="replace")
    except (OSError, ValueError) as exc:
        return f"Could not read the file safely: {type(exc).__name__}: {exc}"
    return f"Contents of {current}:\n\n{text_content}"


def _operation_child_path(location: str, filename: str) -> Path:
    """Resolve one plain file name in an approved user folder; reject links and paths."""
    base = normalize_location(location)
    raw = str(filename).strip()
    if (
        not raw
        or raw in {".", ".."}
        or Path(raw).name != raw
        or any(c in raw for c in '<>:"/\\|?*')
        or any(ord(c) < 32 for c in raw)
    ):
        raise ValueError("Use a simple file name without a path or reserved/control characters.")
    candidate = base / raw
    if candidate.is_symlink():
        raise ValueError("Symbolic links are not supported for file operations.")
    return safe_child_path(location, raw)



SUPPORTED_OPEN_FILE_SUFFIXES = {
    ".txt", ".md", ".csv", ".json", ".log", ".pdf",
    ".doc", ".docx", ".rtf", ".odt",
    ".xls", ".xlsx", ".ods",
    ".ppt", ".pptx", ".odp",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff",
}


def _is_windows_platform() -> bool:
    return os.name == "nt"


def _launch_file_with_default_app(path: Path) -> None:
    """Ask Windows Shell to open a user-selected document/image with its default app."""
    os.startfile(str(path))  # type: ignore[attr-defined]


MAX_DUPLICATE_SCAN_FILES = 5000
MAX_DUPLICATE_HASH_BYTES = 256 * 1024 * 1024
MAX_DUPLICATE_SINGLE_FILE_BYTES = 100 * 1024 * 1024
MAX_DUPLICATE_GROUPS = 20
MAX_DUPLICATE_PATHS_PER_GROUP = 10
DUPLICATE_IGNORED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "AppData",
    "System Volume Information", "$Recycle.Bin", ".cache", ".next", "dist", "build",
}


def _sha256_if_unchanged(path: Path, expected: os.stat_result) -> str | None:
    """Hash a regular file only if both the open handle and final path still match."""
    try:
        if path.is_symlink():
            return None
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            identity_expected = (
                expected.st_dev, expected.st_ino, expected.st_size, expected.st_mtime_ns
            )
            if identity_before != identity_expected:
                return None
            digest = hashlib.sha256()
            byte_count = 0
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                byte_count += len(chunk)
                if byte_count > expected.st_size or byte_count > MAX_DUPLICATE_SINGLE_FILE_BYTES:
                    return None
                digest.update(chunk)
            after = os.fstat(stream.fileno())
            identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        final_path_stat = path.stat()
        final_path_identity = (
            final_path_stat.st_dev, final_path_stat.st_ino,
            final_path_stat.st_size, final_path_stat.st_mtime_ns,
        )
        if (
            identity_after != identity_before
            or final_path_identity != identity_before
            or byte_count != expected.st_size
            or path.is_symlink()
        ):
            return None
        return digest.hexdigest()
    except OSError:
        return None


def find_duplicate_files(location: str, approve) -> str:
    """Find identical files by SHA-256 in a bounded approved folder scope; never modify files."""
    label = str(location).strip()
    if label.casefold() == "all":
        selected_roots = [
            ("Desktop", ROOTS["desktop"]),
            ("Documents", ROOTS["documents"]),
            ("Downloads", ROOTS["downloads"]),
        ]
    else:
        aliases = {
            "desktop": "desktop", "documents": "documents", "downloads": "downloads",
            "ডেস্কটপ": "desktop", "ডকুমেন্টস": "documents", "ডাউনলোডস": "downloads",
        }
        key = aliases.get(label.casefold())
        if key is None:
            return "Location must be Desktop, Documents, Downloads, or All."
        selected_roots = [(label.title(), ROOTS[key])]

    scope = ", ".join(root_label for root_label, _root in selected_roots)
    confirmation = (
        f"Find duplicate files in: {scope}\n\n"
        f"J.A.R.V.I.S will recursively inspect file names and sizes, then hash only same-size candidates. "
        f"It can examine at most {MAX_DUPLICATE_SCAN_FILES:,} file entries and hash at most "
        f"{MAX_DUPLICATE_HASH_BYTES // (1024 * 1024)} MiB total; individual files above "
        f"{MAX_DUPLICATE_SINGLE_FILE_BYTES // (1024 * 1024)} MiB are skipped.\n\n"
        "Matching file paths, sizes, and shortened SHA-256 fingerprints will be returned to the AI conversation "
        "and may be sent to the configured AI provider. File contents themselves are not included in the results. "
        "No files will be deleted, moved, renamed, or edited. Approve this local scan?"
    )
    try:
        if not approve("Confirm duplicate-file scan", confirmation):
            return "Cancelled. No duplicate-file scan was started."
    except Exception as exc:
        return f"Could not obtain approval ({type(exc).__name__}). No duplicate-file scan was started."

    entries_scanned = 0
    large_files_skipped = 0
    hash_bytes = 0
    budget_groups_skipped = 0
    changed_files_skipped = 0
    scan_limit_hit = False
    size_candidates: dict[int, list[tuple[Path, os.stat_result, Path]]] = {}
    ignored_names = {name.casefold() for name in DUPLICATE_IGNORED_DIRS}

    for root_label, root in selected_roots:
        if not root.exists():
            continue
        try:
            root_resolved = root.resolve()
        except OSError:
            continue
        stop_scan = False
        for current_dir, directories, filenames in os.walk(root, topdown=True, followlinks=False):
            current_path = Path(current_dir)
            directories[:] = [
                name for name in directories
                if not name.startswith(".")
                and name.casefold() not in ignored_names
                and not (current_path / name).is_symlink()
            ]
            for filename in filenames:
                if entries_scanned >= MAX_DUPLICATE_SCAN_FILES:
                    scan_limit_hit = True
                    stop_scan = True
                    break
                entries_scanned += 1
                path = current_path / filename
                if path.is_symlink() or filename.startswith("."):
                    continue
                try:
                    resolved = path.resolve(strict=True)
                    if not resolved.is_relative_to(root_resolved) or not path.is_file():
                        continue
                    metadata = path.stat()
                except OSError:
                    continue
                if metadata.st_size > MAX_DUPLICATE_SINGLE_FILE_BYTES:
                    large_files_skipped += 1
                    continue
                size_candidates.setdefault(metadata.st_size, []).append((path, metadata, root_resolved))
            if stop_scan:
                break
        if scan_limit_hit:
            break

    duplicate_candidates: dict[tuple[int, str], list[Path]] = {}
    for size, candidates in sorted(size_candidates.items()):
        if len(candidates) < 2:
            continue
        group_bytes = size * len(candidates)
        if hash_bytes + group_bytes > MAX_DUPLICATE_HASH_BYTES:
            budget_groups_skipped += 1
            continue
        for path, metadata, _root_resolved in candidates:
            digest = _sha256_if_unchanged(path, metadata)
            if digest is None:
                changed_files_skipped += 1
                continue
            hash_bytes += metadata.st_size
            duplicate_candidates.setdefault((size, digest), []).append(path)

    groups = [
        (size, digest, sorted(paths, key=lambda item: str(item).casefold()))
        for (size, digest), paths in duplicate_candidates.items()
        if len(paths) > 1
    ]
    groups.sort(key=lambda item: (-item[0] * (len(item[2]) - 1), str(item[2][0]).casefold()))
    redundant_bytes = sum(size * (len(paths) - 1) for size, _digest, paths in groups)
    if not groups:
        summary = f"No identical-file groups were confirmed in {scope}. Scanned {entries_scanned:,} file entr(y/ies)."
    else:
        summary = (
            f"Found {len(groups):,} duplicate group(s) in {scope}; "
            f"about {redundant_bytes:,} bytes are repeated beyond one copy. "
            f"Scanned {entries_scanned:,} file entr(y/ies), hashed {hash_bytes:,} bytes:\n"
        )
        for group_number, (size, digest, paths) in enumerate(groups[:MAX_DUPLICATE_GROUPS], start=1):
            summary += (
                f"\n{group_number}. {len(paths)} identical files — {size:,} bytes each — "
                f"SHA-256 {digest[:12]}…\n"
            )
            shown = paths[:MAX_DUPLICATE_PATHS_PER_GROUP]
            summary += "\n".join(f"   - {path}" for path in shown)
            if len(paths) > len(shown):
                summary += f"\n   - … and {len(paths) - len(shown)} more path(s)"
            summary += "\n"
        if len(groups) > MAX_DUPLICATE_GROUPS:
            summary += f"\nOnly the first {MAX_DUPLICATE_GROUPS} duplicate groups are shown."

    notes = []
    if large_files_skipped:
        notes.append(f"skipped {large_files_skipped:,} file(s) larger than {MAX_DUPLICATE_SINGLE_FILE_BYTES:,} bytes")
    if budget_groups_skipped:
        notes.append(f"skipped {budget_groups_skipped:,} same-size group(s) due to the hash budget")
    if changed_files_skipped:
        notes.append(f"skipped {changed_files_skipped:,} file(s) that changed or could not be read consistently")
    if scan_limit_hit:
        notes.append(f"stopped at the {MAX_DUPLICATE_SCAN_FILES:,}-entry scan limit")
    if notes:
        summary += "\n\nScan limits: " + "; ".join(notes) + "."
    summary += "\n\nNo files were changed or deleted."
    return summary


MAX_ARCHIVE_FILES = 100
MAX_ARCHIVE_TOTAL_BYTES = 100 * 1024 * 1024


def create_zip_archive(location: str, filenames: list[str], archive_filename: str, approve) -> str:
    """Create a bounded flat ZIP from user-selected regular files, without overwriting anything."""
    if not isinstance(filenames, list) or not filenames:
        return "Choose at least one filename to archive."
    if len(filenames) > MAX_ARCHIVE_FILES:
        return f"A ZIP archive can contain at most {MAX_ARCHIVE_FILES} files per operation."
    if any(not isinstance(name, str) for name in filenames):
        return "Each selected item must be a filename, not a path or another value."
    if len({name.casefold() for name in filenames}) != len(filenames):
        return "Duplicate filenames are not allowed in one archive."
    if not isinstance(archive_filename, str) or not archive_filename.strip().lower().endswith(".zip"):
        return "The archive filename must end with .zip."
    try:
        destination = _operation_child_path(location, archive_filename)
    except (ValueError, OSError) as exc:
        return f"ZIP creation blocked: {exc}"
    if destination.exists():
        return f"Archive destination already exists: {destination}. Nothing was overwritten."

    source_records: list[tuple[Path, os.stat_result]] = []
    total_size = 0
    try:
        for filename in filenames:
            source = _operation_child_path(location, filename)
            if source == destination:
                return "The archive cannot also be one of its source files."
            if not source.is_file():
                return f"Selected source is missing or is not a regular file: {source}"
            metadata = source.stat()
            if source.is_symlink():
                return f"Symbolic links are not supported: {source}"
            total_size += metadata.st_size
            if total_size > MAX_ARCHIVE_TOTAL_BYTES:
                return (
                    f"Selected files total more than {MAX_ARCHIVE_TOTAL_BYTES // (1024 * 1024)} MiB. "
                    "Choose a smaller set and try again."
                )
            source_records.append((source, metadata))
    except (ValueError, OSError) as exc:
        return f"ZIP creation blocked: {exc}"

    if len({source.name.casefold() for source, _metadata in source_records}) != len(source_records):
        return "Two selected files resolve to the same archive entry name; choose unique filenames."

    detail_lines = [
        "Create a ZIP archive from these files?",
        "",
        f"Folder: {destination.parent}",
        f"Archive: {destination.name}",
        f"Destination: {destination}",
        f"Selected files: {len(source_records)}",
        f"Total uncompressed size: {total_size:,} bytes",
        "",
        "Sources (files will remain unchanged):",
    ]
    detail_lines.extend(
        f"  • {source.name} — {metadata.st_size:,} bytes"
        for source, metadata in source_records
    )
    detail_lines.extend([
        "",
        "The new archive will be created only if its destination does not exist. "
        "Approve creating this exact ZIP archive?"
    ])
    try:
        if not approve("Confirm ZIP archive creation", "\n".join(detail_lines)):
            return "Cancelled. No ZIP archive was created."
    except Exception as exc:
        return f"Could not obtain approval ({type(exc).__name__}). No ZIP archive was created."

    temp_path = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        # Recheck the output and every source after user approval.
        if destination.exists():
            return f"Archive destination appeared after confirmation: {destination}. Nothing was overwritten."
        for source, original in source_records:
            current = _operation_child_path(location, source.name)
            now = current.stat()
            original_identity = (original.st_dev, original.st_ino, original.st_size, original.st_mtime_ns)
            current_identity = (now.st_dev, now.st_ino, now.st_size, now.st_mtime_ns)
            if current != source or current.is_symlink() or current_identity != original_identity:
                return f"Selected file changed after confirmation: {source.name}. No archive was published."

        actual_total = 0
        with zipfile.ZipFile(
            temp_path,
            mode="x",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=False,
        ) as archive:
            for source, original in source_records:
                with source.open("rb") as source_stream:
                    opened = os.fstat(source_stream.fileno())
                    opened_identity = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
                    expected_identity = (original.st_dev, original.st_ino, original.st_size, original.st_mtime_ns)
                    if opened_identity != expected_identity:
                        raise ValueError(f"Selected file changed while opening: {source.name}")
                    written_for_source = 0
                    with archive.open(source.name, mode="w", force_zip64=False) as archive_stream:
                        while True:
                            chunk = source_stream.read(1024 * 1024)
                            if not chunk:
                                break
                            written_for_source += len(chunk)
                            actual_total += len(chunk)
                            if actual_total > MAX_ARCHIVE_TOTAL_BYTES:
                                raise ValueError("Selected files grew beyond the 100 MiB archive limit.")
                            archive_stream.write(chunk)
                    after_read = os.fstat(source_stream.fileno())
                    after_identity = (
                        after_read.st_dev, after_read.st_ino, after_read.st_size, after_read.st_mtime_ns
                    )
                    if after_identity != opened_identity or written_for_source != original.st_size:
                        raise ValueError(f"Selected file changed while archiving: {source.name}")
                    # The path itself must still name the file that was approved and opened.
                    path_after = source.stat()
                    path_identity = (
                        path_after.st_dev, path_after.st_ino, path_after.st_size, path_after.st_mtime_ns
                    )
                    if source.is_symlink() or path_identity != opened_identity:
                        raise ValueError(f"Selected file path changed while archiving: {source.name}")

        if destination.exists():
            return f"Archive destination appeared before commit: {destination}. Nothing was overwritten."
        # A same-directory hard-link is an atomic no-overwrite publish on supported filesystems.
        # If the filesystem disallows hard links, fail closed and preserve the existing destination.
        try:
            os.link(temp_path, destination)
        except FileExistsError:
            return f"Archive destination already exists: {destination}. Nothing was overwritten."
        except OSError as exc:
            return (
                f"ZIP was prepared but could not be published safely ({type(exc).__name__}). "
                "The destination was not overwritten; try a local folder on a supported filesystem."
            )
        archive_size = destination.stat().st_size
        return (
            f"Created ZIP archive: {destination} "
            f"({len(source_records)} files, {archive_size:,} bytes). Source files were left unchanged."
        )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return f"ZIP creation stopped safely ({type(exc).__name__}): {exc}. No partial archive was published."
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def move_file_to_recycle_bin(location: str, filename: str, approve) -> str:
    """Send one approved regular file to the OS recycle bin/trash, never permanent-delete."""
    try:
        path = _operation_child_path(location, filename)
    except (ValueError, OSError) as exc:
        return f"Recycle Bin operation blocked: {exc}"
    if not _is_windows_platform():
        return "Sending files to the Windows Recycle Bin is supported only on Windows."
    if not path.is_file():
        return f"File not found or not a regular file: {path}"
    try:
        before = path.stat()
    except OSError as exc:
        return f"Could not inspect the file before recycle: {exc}"
    detail = (
        f"Send this file to the Windows Recycle Bin? It will not be permanently deleted.\n\n"
        f"File: {path}\n"
        f"Size: {before.st_size:,} bytes\n"
        f"Type: {path.suffix.lower() or 'no extension'}\n\n"
        "The file should remain recoverable from the Recycle Bin until it is emptied. "
        "Approve moving this exact file to the Recycle Bin?"
    )
    try:
        if not approve("Move file to Recycle Bin", detail):
            return "Cancelled. The file was not moved to the Recycle Bin."
    except Exception as exc:
        return f"Could not obtain approval ({type(exc).__name__}). The file was not moved."

    try:
        current = _operation_child_path(location, filename)
        after = current.stat()
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if current != path or identity_after != identity_before:
            return "The file changed after confirmation. Nothing was moved; review it and try again."
        from send2trash import send2trash
        send2trash(str(current))
    except (OSError, ValueError) as exc:
        return f"Could not move the file to the Recycle Bin: {type(exc).__name__}: {exc}"
    except Exception as exc:
        return f"Recycle Bin operation failed safely ({type(exc).__name__}). The app cannot confirm that the file was moved."
    return f"Moved to the Windows Recycle Bin: {path}. Verify it in the Recycle Bin if needed."


def open_file(location: str, filename: str, approve) -> str:
    """Open one allow-listed document/image from an approved user folder after confirmation."""
    try:
        path = _operation_child_path(location, filename)
    except (ValueError, OSError) as exc:
        return f"File open blocked: {exc}"
    if path.suffix.lower() not in SUPPORTED_OPEN_FILE_SUFFIXES:
        return (
            "For safety, only common document, data and image formats can be opened: "
            + ", ".join(sorted(SUPPORTED_OPEN_FILE_SUFFIXES))
            + ". Executables and scripts are blocked."
        )
    if not path.is_file():
        return f"File not found or not a regular file: {path}"
    if not _is_windows_platform():
        return "Opening files with their Windows default application is supported only on Windows."
    try:
        before = path.stat()
    except OSError as exc:
        return f"Could not inspect the file before opening: {exc}"
    detail = (
        f"Open this file in its default Windows application?\n\n"
        f"File: {path}\n"
        f"Type: {path.suffix.lower()}\n"
        f"Size: {before.st_size:,} bytes\n\n"
        "J.A.R.V.I.S will not edit or submit the file. The associated application may have its own behavior."
    )
    try:
        if not approve("Confirm open file", detail):
            return "Cancelled. The file was not opened."
    except Exception as exc:
        return f"Could not obtain approval ({type(exc).__name__}). The file was not opened."
    try:
        # Re-check the path and metadata after the dialog to avoid opening a swapped link/file.
        current = _operation_child_path(location, filename)
        after = current.stat()
        if current != path or not current.is_file():
            return "The selected file changed after confirmation. Nothing was opened."
        if (after.st_size, after.st_mtime_ns, after.st_ino) != (before.st_size, before.st_mtime_ns, before.st_ino):
            return "The file changed after confirmation. Please review it and try again."
        _launch_file_with_default_app(current)
    except (OSError, ValueError) as exc:
        return f"Could not open the file: {exc}"
    except Exception as exc:
        return f"Opening the file failed safely ({type(exc).__name__}): {exc}"
    return f"Asked Windows to open: {path}. Verify that the expected application and file are visible."


def _copy_file_no_overwrite(source: Path, destination: Path) -> None:
    """Copy one regular file without ever opening an existing destination for writing."""
    created_destination = False
    try:
        with source.open("rb") as source_stream:
            # Exclusive creation is the no-overwrite guard, including a destination
            # that appears after the approval dialog was shown.
            with destination.open("xb") as destination_stream:
                created_destination = True
                shutil.copyfileobj(source_stream, destination_stream, length=1024 * 1024)
                destination_stream.flush()
                os.fsync(destination_stream.fileno())
        try:
            shutil.copystat(source, destination, follow_symlinks=False)
        except OSError:
            # Metadata preservation is best-effort; the copied file data is intact.
            pass
    except Exception:
        if created_destination:
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def _transfer_file(
    operation: str,
    source_location: str,
    filename: str,
    destination_location: str,
    destination_filename: str,
    approve,
) -> str:
    """Copy, move or rename one file, with explicit approval and no-overwrite behavior."""
    if operation not in {"copy", "move", "rename"}:
        return "Blocked: unsupported file operation."
    try:
        source = _operation_child_path(source_location, filename)
        destination = _operation_child_path(destination_location, destination_filename)
    except (ValueError, OSError) as exc:
        return f"File operation blocked: {exc}"

    if source == destination:
        return "Source and destination are the same file. Nothing was changed."
    if operation == "rename" and source.parent != destination.parent:
        return "Rename must stay inside the same approved folder. Use move to change folders."
    if not source.is_file():
        return f"Source file not found or is not a regular file: {source}"
    if destination.exists():
        return f"Destination already exists: {destination}. Nothing was overwritten."

    try:
        size = source.stat().st_size
    except OSError as exc:
        return f"Could not inspect the source file: {exc}"

    action = {"copy": "Copy file", "move": "Move file", "rename": "Rename file"}[operation]
    if operation == "copy":
        effect = "The source stays in place."
    else:
        effect = "The source is removed only after the destination copy succeeds."
    approval_text = (
        f"Operation: {operation.upper()}\n\n"
        f"Source: {source}\n"
        f"Destination: {destination}\n"
        f"File size: {size:,} bytes\n\n"
        f"{effect}\n"
        "An existing destination will never be overwritten. Approve this exact operation?"
    )
    try:
        approved = approve(action, approval_text)
    except Exception as exc:
        return f"Could not obtain approval ({type(exc).__name__}). Nothing was changed."
    if not approved:
        return f"Cancelled. No file was {('copied' if operation == 'copy' else 'moved or renamed')}."

    try:
        _copy_file_no_overwrite(source, destination)
    except FileExistsError:
        return f"Destination appeared or already exists: {destination}. No file was overwritten."
    except OSError as exc:
        return f"File operation failed safely ({type(exc).__name__}): {exc}"

    copied_size = destination.stat().st_size
    if operation == "copy":
        return f"Copied file: {source} → {destination} ({copied_size:,} bytes)."
    try:
        source.unlink()
    except OSError as exc:
        return (
            f"Destination copy completed at {destination}, but the original source could not be removed "
            f"({exc}). Both files remain; no data was lost."
        )
    label = "Renamed" if operation == "rename" else "Moved"
    return f"{label} file: {source} → {destination} ({copied_size:,} bytes); original removed after copy succeeded."


def copy_file(
    source_location: str,
    filename: str,
    destination_location: str,
    destination_filename: str,
    approve,
) -> str:
    """Copy one file between approved user folders, with an explicit confirmation."""
    return _transfer_file(
        "copy", source_location, filename, destination_location, destination_filename, approve
    )


def move_file(
    source_location: str,
    filename: str,
    destination_location: str,
    destination_filename: str,
    approve,
) -> str:
    """Move one file between approved user folders, without overwriting a destination."""
    return _transfer_file(
        "move", source_location, filename, destination_location, destination_filename, approve
    )


def rename_file(location: str, filename: str, new_filename: str, approve) -> str:
    """Rename one file inside Desktop, Documents or Downloads, with confirmation."""
    return _transfer_file("rename", location, filename, location, new_filename, approve)


def direct_command(text: str) -> str | None:
    """Handle common app, folder, web, and basic system commands locally."""
    value = text.strip()
    low = value.casefold().strip(".!? ")

    if low in {"system information", "system info", "computer information", "show system info", "সিস্টেম তথ্য", "কম্পিউটারের তথ্য", "সিস্টেম ইনফো"}:
        return get_system_info()

    # Common exact browser/folder commands first.
    if low in {"youtube kholo", "open youtube", "ইউটিউব খোলো", "ইউটিউব চালু করো"}:
        return open_website("https://www.youtube.com")
    if low in {"google kholo", "open google", "গুগল খোলো", "গুগল চালু করো"}:
        return open_website("https://www.google.com")
    if low in {"desktop kholo", "open desktop", "ডেস্কটপ খোলো", "ডেস্কটপ খুলে দাও"}:
        return open_folder("desktop")
    if low in {"downloads kholo", "open downloads", "ডাউনলোডস খোলো", "ডাউনলোড ফোল্ডার খোলো", "ডাউনলোডস খুলে দাও"}:
        return open_folder("downloads")
    if low in {"documents kholo", "open documents", "ডকুমেন্টস খোলো", "ডকুমেন্টস খুলে দাও"}:
        return open_folder("documents")

    # Web-search commands.
    for trigger in ["google e search koro ", "search web for ", "google search ", "গুগলে সার্চ করো ", "গুগলে খোঁজো "]:
        if trigger in low:
            query = value[low.index(trigger) + len(trigger):].strip()
            return open_website(query) if query else None

    # Only resolve known app names locally. Other natural-language requests should
    # be passed to the configured model instead of incorrectly treated as an app.
    candidates: list[str] = []
    for trigger in ["open ", "launch ", "খোলো ", "চালু করো ", "চালু কর ", "খুলে দাও "]:
        if low.startswith(trigger):
            candidates.append(value[len(trigger):].strip(" .!?"))
    for suffix in [" চালু করো", " খোলো", " kholo", " খুলে দাও"]:
        if low.endswith(suffix):
            candidates.append(value[:-len(suffix)].strip())

    known_special = {"chrome", "edge", "browser", "google", "youtube", "settings", "web browser", *WORKSPACE_WEBSITE_ALIASES.keys()}
    for name in candidates:
        key = name.casefold()
        if key in APP_ALIASES or key in known_special:
            if key == "google":
                return open_website("https://www.google.com")
            if key == "youtube":
                return open_website("https://www.youtube.com")
            if key in WORKSPACE_WEBSITE_ALIASES:
                return open_website(name)
            return open_application(name)
    return None
