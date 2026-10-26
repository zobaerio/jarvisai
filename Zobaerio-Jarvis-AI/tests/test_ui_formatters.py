from datetime import datetime

from jarvis.ui_formatters import format_header_clock


def test_format_header_clock_uses_24_hour_time_and_uppercase_date():
    value = datetime(2026, 10, 26, 18, 7, 5)
    assert format_header_clock(value) == "18:07:05\nMON, 26 OCT"


def test_format_header_clock_pads_single_digit_fields():
    value = datetime(2026, 1, 3, 4, 2, 9)
    assert format_header_clock(value) == "04:02:09\nSAT, 03 JAN"
