from datetime import datetime

from jarvis.ui_formatters import format_header_clock


def test_format_header_clock_uses_24_hour_time_and_uppercase_date():
    value = datetime(2026, 10, 26, 18, 7, 5)
    assert format_header_clock(value) == "18:07:05\nMON, 26 OCT"


def test_format_header_clock_pads_single_digit_fields():
    value = datetime(2026, 1, 3, 4, 2, 9)
    assert format_header_clock(value) == "04:02:09\nSAT, 03 JAN"


from jarvis.ui_formatters import bounded_int


def test_bounded_int_clamps_values_to_inclusive_bounds():
    assert bounded_int(500, 92, 80, 320) == 320
    assert bounded_int(-10, 92, 80, 320) == 80
    assert bounded_int(164, 92, 80, 320) == 164


def test_bounded_int_uses_fallback_for_invalid_settings():
    assert bounded_int("not-a-number", 164, 104, 400) == 164
    assert bounded_int(None, 164, 104, 400) == 164
    assert bounded_int(float("inf"), 164, 104, 400) == 164


def test_bounded_int_handles_string_integer_settings():
    assert bounded_int("240", 92, 80, 320) == 240


def test_bounded_int_sanitizes_invalid_fallback_values():
    assert bounded_int("invalid", "not-a-number", 80, 320) == 80
    assert bounded_int(None, float("inf"), 80, 320) == 80
    assert bounded_int(None, float("-inf"), 80, 320) == 80
    assert bounded_int(None, 500, 80, 320) == 320
    assert bounded_int(None, 10, 80, 320) == 80


from jarvis.ui_formatters import bounded_float


def test_bounded_float_clamps_opacity_to_supported_range():
    assert bounded_float(1.5, 1.0, 0.55, 1.0) == 1.0
    assert bounded_float(0.1, 1.0, 0.55, 1.0) == 0.55
    assert bounded_float(0.8, 1.0, 0.55, 1.0) == 0.8


def test_bounded_float_uses_fallback_for_invalid_or_non_finite_settings():
    assert bounded_float("invalid", 1.0, 0.55, 1.0) == 1.0
    assert bounded_float(None, 1.0, 0.55, 1.0) == 1.0
    assert bounded_float(float("nan"), 0.9, 0.55, 1.0) == 0.9
    assert bounded_float(float("inf"), 0.9, 0.55, 1.0) == 0.9
    assert bounded_float(float("-inf"), 0.9, 0.55, 1.0) == 0.9


def test_bounded_float_keeps_fallback_finite_and_within_bounds():
    assert bounded_float(None, float("nan"), 0.55, 1.0) == 0.55
    assert bounded_float(None, float("inf"), 0.55, 1.0) == 0.55
    assert bounded_float(None, -float("inf"), 0.55, 1.0) == 0.55
    assert bounded_float(None, 5.0, 0.55, 1.0) == 1.0
    assert bounded_float(None, 0.1, 0.55, 1.0) == 0.55


def test_bounded_float_sanitizes_invalid_fallback_values():
    assert bounded_float("invalid", float("nan"), 0.55, 1.0) == 0.55
    assert bounded_float(None, float("inf"), 0.55, 1.0) == 0.55
    assert bounded_float(None, "not-a-number", 0.55, 1.0) == 0.55
    assert bounded_float(None, 5.0, 0.55, 1.0) == 1.0
    assert bounded_float(None, 0.1, 0.55, 1.0) == 0.55
