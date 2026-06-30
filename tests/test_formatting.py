"""Formatação de tempo (MM:SS)."""

import pytest

from src.utils.formatting import format_time


@pytest.mark.parametrize("secs, esperado", [
    (0, "00:00"),
    (5, "00:05"),
    (59, "00:59"),
    (60, "01:00"),
    (75, "01:15"),
    (600, "10:00"),
    (3599, "59:59"),
    (12.9, "00:12"),     # float é truncado por int()
    ("abc", "00:00"),    # erro -> fallback
    (None, "00:00"),     # erro -> fallback
])
def test_format_time(secs, esperado):
    assert format_time(secs) == esperado
