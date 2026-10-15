"""Win32 system-tray icon via ctypes (no third-party dependency).

Creates its own hidden HWND with a minimal WndProc; the message pump is the
host Tk mainloop (it dispatches *all* thread windows, not just Tk's own),
so no extra thread is needed. All public methods must be called from the
Tk (main) thread.

Right-click opens a context menu rebuilt on every open (labels reflect
live state, e.g. service running/stopped). Left double-click opens history.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Callable

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

WM_APP = 0x8000
WM_TRAYICON = WM_APP + 1
WM_RBUTTONUP = 0x0205
WM_LBUTTONDBLCLK = 0x0203
WM_COMMAND = 0x0111
WM_DESTROY = 0x0002

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_RETURNCMD = 0x0100
TPM_RIGHTBUTTON = 0x0002

IDI_APPLICATION = 32512

ID_TOGGLE = 101
ID_HISTORY = 102
ID_SETTINGS = 103
ID_QUIT = 104


class NOTIFYICONDATA(ctypes.Structure):    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


def _bind_win32() -> None:
    """Declare exact Win32 signatures (64-bit safe; no c_int truncation)."""
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.DefWindowProcW.restype = ctypes.c_ssize_t
    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    user32.RegisterClassW.restype = wintypes.WORD
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
    ]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
    user32.LoadIconW.restype = wintypes.HICON
    shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATA)]
    shell32.Shell_NotifyIconW.restype = wintypes.BOOL
    user32.CreatePopupMenu.restype = wintypes.HMENU
    user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
    user32.AppendMenuW.restype = wintypes.BOOL
    user32.TrackPopupMenu.argtypes = [
        wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, wintypes.HWND, wintypes.LPVOID,
    ]
    user32.TrackPopupMenu.restype = wintypes.BOOL
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.DestroyMenu.argtypes = [wintypes.HMENU]
    user32.DestroyMenu.restype = wintypes.BOOL
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.DestroyWindow.restype = wintypes.BOOL


class WNDCLASSW(ctypes.Structure):
    """Win32 window class (ctypes.wintypes does not provide it)."""

    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


_bind_win32()  # after WNDCLASSW/NOTIFYICONDATA exist


class WinTray:
    """Resident tray icon. Call pump-independent methods from Tk thread."""

    def __init__(
        self,
        on_toggle,
        on_history,
        on_settings,
        on_quit,
        is_running: Callable[[], bool],
    ) -> None:
        self._on_toggle = on_toggle
        self._on_history = on_history
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._is_running = is_running
        self._hwnd = None
        self._nid = None
        self._wndproc_ref = None  # keep alive: Windows calls into it
        self._create_window()
        self._add_icon()

    # -- window ----------------------------------------------------------
    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            event = lparam & 0xFFFF
            if event == WM_RBUTTONUP:
                self._show_menu()
            elif event == WM_LBUTTONDBLCLK:
                try:
                    self._on_history()
                except Exception:
                    pass
            return 0
        if msg == WM_COMMAND:
            cmd = wparam & 0xFFFF
            try:
                if cmd == ID_TOGGLE:
                    self._on_toggle()
                elif cmd == ID_HISTORY:
                    self._on_history()
                elif cmd == ID_SETTINGS:
                    self._on_settings()
                elif cmd == ID_QUIT:
                    self._on_quit()
            except Exception:
                pass
            return 0
        if msg == WM_DESTROY:
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _create_window(self) -> None:
        hinst = kernel32.GetModuleHandleW(None)
        cls_name = "WritingAssistantTray"
        wc = WNDCLASSW()
        wc.lpfnWndProc = WNDPROC(self._wndproc)
        self._wndproc_ref = wc.lpfnWndProc  # prevent GC of the callback
        wc.lpszClassName = cls_name
        wc.hInstance = hinst
        user32.RegisterClassW(ctypes.byref(wc))
        self._hwnd = user32.CreateWindowExW(
            0, cls_name, "Writing Assistant Tray", 0, 0, 0, 0, 0, None, None, hinst, None
        )
        if not self._hwnd:
            raise RuntimeError("Could not create tray helper window")

    # -- icon ------------------------------------------------------------
    def _add_icon(self) -> None:
        # MAKEINTRESOURCE: stock icon id passed as a pseudo-pointer.
        hicon = user32.LoadIconW(None, ctypes.cast(IDI_APPLICATION, wintypes.LPCWSTR))
        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = self._hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAYICON
        nid.hIcon = hicon
        nid.szTip = "Writing Assistant"
        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
            raise RuntimeError("Shell_NotifyIcon ADD failed")
        self._nid = nid

    def refresh_tip(self, running: bool) -> None:
        """Update hover tooltip to reflect service state."""
        if not self._nid:
            return
        try:
            self._nid.szTip = (
                "Writing Assistant (listening Ctrl+Alt+G)"
                if running
                else "Writing Assistant (paused)"
            )
            self._nid.uFlags = NIF_TIP
            shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._nid))
        except Exception:
            pass

    # -- menu ------------------------------------------------------------
    def _show_menu(self) -> None:
        try:
            running = bool(self._is_running())
        except Exception:
            running = True
        menu = user32.CreatePopupMenu()
        try:
            user32.AppendMenuW(menu, MF_STRING, ID_TOGGLE, "Pause service" if running else "Start service")
            user32.AppendMenuW(menu, MF_STRING, ID_HISTORY, "History...")
            user32.AppendMenuW(menu, MF_STRING, ID_SETTINGS, "Settings...")
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, ID_QUIT, "Quit")
            pos = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pos))
            user32.SetForegroundWindow(self._hwnd)
            cmd = user32.TrackPopupMenu(
                menu, TPM_RETURNCMD | TPM_RIGHTBUTTON, pos.x, pos.y, 0, self._hwnd, None
            )
            if cmd:
                # Reuse the WM_COMMAND path for a single handling place.
                self._wndproc(self._hwnd, WM_COMMAND, cmd, 0)
        finally:
            user32.DestroyMenu(menu)

    # -- teardown ----------------------------------------------------------
    def remove(self) -> None:
        try:
            if self._nid:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
                self._nid = None
        except Exception:
            pass
        try:
            if self._hwnd:
                user32.DestroyWindow(self._hwnd)
                self._hwnd = None
        except Exception:
            pass
