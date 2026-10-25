from __future__ import annotations

import os
import platform
import shutil
import subprocess
import webbrowser
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


def open_website(url_or_query: str) -> str:
    value = url_or_query.strip()
    if not value:
        return "Tell me a website or something to search for."
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


def get_system_info() -> str:
    return (
        f"Operating system: {platform.system()} {platform.release()}\n"
        f"Computer: {platform.node()}\n"
        f"Python: {platform.python_version()}\n"
        f"Current time: {datetime.now().astimezone().strftime('%Y-%m-%d %I:%M:%S %p %Z')}"
    )


def safe_child_path(location: str, name: str) -> Path:
    base = normalize_location(location)
    raw = name.strip()
    if not raw or raw in {".", ".."} or Path(raw).name != raw or any(c in raw for c in '<>:"/\\|?*'):
        raise ValueError("Use a simple file/folder name without a path or reserved characters.")
    path = (base / raw).resolve()
    if base.resolve() not in path.parents:
        raise ValueError("That path is outside the allowed folder.")
    return path


def create_folder(location: str, name: str, approve) -> str:
    path = safe_child_path(location, name)
    if path.exists():
        return f"A folder or file already exists at {path}. Nothing was changed."
    if not approve("Create folder", f"Create this folder?\n\n{path}"):
        return "Cancelled. No folder was created."
    path.mkdir(parents=False, exist_ok=False)
    return f"Created folder: {path}"


def create_text_file(location: str, filename: str, content: str, approve) -> str:
    path = safe_child_path(location, filename)
    if path.suffix.lower() not in {".txt", ".md", ".csv", ".json", ".log"}:
        return "For safety, I can create .txt, .md, .csv, .json, or .log files only."
    if path.exists():
        return f"File already exists at {path}. I will not overwrite it."
    if len(content) > 100_000:
        return "The content is too long (maximum 100,000 characters)."
    if not approve("Create file", f"Create this file?\n\n{path}\n\nContent preview:\n{content[:700]}"):
        return "Cancelled. No file was created."
    path.write_text(content, encoding="utf-8")
    return f"Created file: {path}"


def read_text_file(location: str, filename: str) -> str:
    path = safe_child_path(location, filename)
    if path.suffix.lower() not in {".txt", ".md", ".csv", ".json", ".log", ".py", ".yaml", ".yml", ".xml"}:
        return "For safety, I can read common text and source-code files only."
    if not path.is_file():
        return f"File not found: {path}"
    if path.stat().st_size > 100_000:
        return "That file is larger than 100 KB, so I will not read it into the chat."
    return f"Contents of {path}:\n\n{path.read_text(encoding='utf-8', errors='replace')}"


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

    known_special = {"chrome", "edge", "browser", "google", "youtube", "settings", "web browser"}
    for name in candidates:
        key = name.casefold()
        if key in APP_ALIASES or key in known_special:
            if key == "google":
                return open_website("https://www.google.com")
            if key == "youtube":
                return open_website("https://www.youtube.com")
            return open_application(name)
    return None
