"""Windows (Win32) UI adapter: Tkinter frameless popup + global hotkey.

Architecture (ADR-07 / ADR-11): the Python core stays 100% OS-independent.
This adapter is the Windows counterpart of the GNOME Shell extension:
it captures the trigger (Ctrl+Alt+G), reads context, calls the core via
the standard ``--ipc`` subprocess protocol, renders the in-place popup
next to the cursor, and pastes with Shift+Insert on Enter.

Only the standard library is required. ``pywin32``/``keyboard`` are
optional accelerators; every module degrades gracefully to ctypes/tkinter.
"""
