"""Shared geometry helper: anchor a popup next to the cursor with clamping.

Ports the logic of extension/popup.js::_updatePosition to a pure function
so it is unit-testable without a display server.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PopupPlacement:
    x: int
    y: int
    width: int


def clamp_popup_position(
    cursor_x: int,
    cursor_y: int,
    popup_width: int = 520,
    popup_height: int = 300,
    screen_width: int = 1920,
    screen_height: int = 1080,
    offset: int = 15,
    margin: int = 20,
    taskbar_reserve: int = 40,
) -> PopupPlacement:
    """Compute top-left coordinates for the popup near the cursor."""
    x = cursor_x + offset
    if x + popup_width > screen_width - margin:
        x = cursor_x - popup_width - offset
    x = max(margin, min(x, screen_width - popup_width - margin))

    below_space = screen_height - taskbar_reserve - cursor_y
    if below_space >= popup_height + offset:
        y = cursor_y + offset
    else:
        y = cursor_y - popup_height - offset
    y = max(taskbar_reserve, min(y, screen_height - taskbar_reserve - popup_height))
    return PopupPlacement(x=int(x), y=int(y), width=popup_width)
