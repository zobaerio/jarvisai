"""Safe, content-free exception summaries for user-facing J.A.R.V.I.S messages."""
from __future__ import annotations

import re


def safe_exception_type(exc: BaseException) -> str:
    """Return only a short type label, never the exception message."""
    raw_name = type(exc).__name__
    safe_name = re.sub(r"[^A-Za-z0-9_]", "", raw_name)[:80]
    return safe_name or "Error"


def safe_tool_error(exc: BaseException) -> str:
    """Return a tool error that can safely be shown to the model/user."""
    return (
        f"Tool failed safely ({safe_exception_type(exc)}). "
        "Sensitive exception details were withheld; check permissions/settings and try again."
    )


def safe_worker_error(exc: BaseException) -> str:
    """Return a Bengali desktop error without echoing internal exception text."""
    return (
        f"একটি সমস্যা হয়েছে ({safe_exception_type(exc)})। "
        "নিরাপত্তার জন্য বিস্তারিত error লুকানো হয়েছে। Settings ও permissions যাচাই করে আবার চেষ্টা করুন।"
    )
