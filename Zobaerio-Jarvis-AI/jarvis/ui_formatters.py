"""Small, deterministic formatters used by the desktop UI."""

from datetime import datetime


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
