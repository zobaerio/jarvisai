"""Launch the local J.A.R.V.I.S procedural 3D character studio."""
from __future__ import annotations

import http.server
import threading
import webbrowser
from functools import partial
from pathlib import Path
from socketserver import ThreadingTCPServer

_SERVER: ThreadingTCPServer | None = None
_LOCK = threading.Lock()


def launch_avatar_studio(character: str = "luna") -> bool:
    """Serve the 3D page on loopback only and open it in the default browser."""
    global _SERVER
    key = character.strip().lower()
    if key not in {"luna", "ruby", "maya"}:
        key = "luna"
    project_root = Path(__file__).resolve().parent.parent
    if not (project_root / "assets" / "avatar_studio.html").is_file():
        raise FileNotFoundError("assets/avatar_studio.html was not found")
    with _LOCK:
        if _SERVER is None:
            handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(project_root))

            class LocalServer(ThreadingTCPServer):
                allow_reuse_address = True
                daemon_threads = True

            _SERVER = LocalServer(("127.0.0.1", 0), handler)
            threading.Thread(target=_SERVER.serve_forever, name="Jarvis3DStudioServer", daemon=True).start()
        port = _SERVER.server_address[1]
    url = f"http://127.0.0.1:{port}/assets/avatar_studio.html?character={key}"
    return bool(webbrowser.open_new_tab(url))
