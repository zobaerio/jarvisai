"""Small, deterministic formatters used by the desktop UI."""

from datetime import datetime


def format_header_clock(value: datetime) -> str:
    """Format local time and date for the compact two-line app header."""
    return f"{value:%H:%M:%S}\n{value:%a, %d %b}".upper()
