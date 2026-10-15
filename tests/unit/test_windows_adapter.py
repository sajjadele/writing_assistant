"""Unit tests for the Windows adapter geometry (no display required)."""

from writing_companion.adapters.windows.placement import clamp_popup_position


def test_popup_opens_below_cursor_with_room():
    p = clamp_popup_position(200, 200, 520, 300, 1920, 1080)
    assert p.x == 215
    assert p.y == 215


def test_popup_flips_left_near_right_edge():
    p = clamp_popup_position(1800, 200, 520, 300, 1920, 1080)
    assert p.x == 1800 - 520 - 15
    assert p.y == 215


def test_popup_opens_above_cursor_without_room_below():
    p = clamp_popup_position(200, 900, 520, 300, 1920, 1080)
    assert p.y == 900 - 300 - 15
    assert p.y >= 40
