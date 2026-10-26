"""Small, deterministic formatters used by the desktop UI."""

from datetime import datetime
import math


def format_header_clock(value: datetime) -> str:
    """Format local time and date for the compact two-line app header."""
    return f"{value:%H:%M:%S}\n{value:%a, %d %b}".upper()


def bounded_int(value: object, fallback: int, minimum: int, maximum: int) -> int:
    """Convert a setting to an integer and clamp it to a safe inclusive range."""
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        parsed = fallback
    return max(minimum, min(parsed, maximum))


def bounded_float(value: object, fallback: float, minimum: float, maximum: float) -> float:
    """Convert a setting to a finite float and clamp it to an inclusive range."""
    try:
        safe_fallback = float(fallback)
        if not math.isfinite(safe_fallback):
            safe_fallback = minimum
    except (TypeError, ValueError, OverflowError):
        safe_fallback = minimum
    safe_fallback = max(minimum, min(safe_fallback, maximum))

    try:
        parsed = float(value)
        if not math.isfinite(parsed):
            parsed = safe_fallback
    except (TypeError, ValueError, OverflowError):
        parsed = safe_fallback
    return max(minimum, min(parsed, maximum))
