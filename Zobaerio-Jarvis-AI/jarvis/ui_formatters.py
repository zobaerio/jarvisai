"""Small, deterministic formatters used by the desktop UI."""

from datetime import datetime
import math


def format_header_clock(value: datetime) -> str:
    """Format local time and date for the compact two-line app header."""
    return f"{value:%H:%M:%S}\n{value:%a, %d %b}".upper()


def bounded_int(value: object, fallback: int, minimum: int, maximum: int) -> int:
    """Convert a setting to an integer and clamp it to a safe inclusive range."""
    try:
        safe_fallback = int(fallback)
    except (TypeError, ValueError, OverflowError):
        safe_fallback = minimum
    safe_fallback = max(minimum, min(safe_fallback, maximum))

    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        parsed = safe_fallback
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

def bounded_window_origin(
    x: object,
    y: object,
    window_width: object,
    window_height: object,
    screen_width: object,
    screen_height: object,
    fallback_x: int = 24,
    fallback_y: int = 120,
) -> tuple[int, int]:
    """Keep a saved window origin inside the visible screen area."""
    safe_screen_width = bounded_int(screen_width, 1, 1, 100_000)
    safe_screen_height = bounded_int(screen_height, 1, 1, 100_000)
    safe_window_width = bounded_int(window_width, 1, 1, 100_000)
    safe_window_height = bounded_int(window_height, 1, 1, 100_000)
    max_x = max(0, safe_screen_width - safe_window_width)
    max_y = max(0, safe_screen_height - safe_window_height)
    return (
        bounded_int(x, fallback_x, 0, max_x),
        bounded_int(y, fallback_y, 0, max_y),
    )
