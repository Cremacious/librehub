"""Active-window -> Steam AppID detection.

On X11 this reads the focused window (``xprop``) and maps it to a Steam
AppID. Wayland has no equivalent "which window is focused" query for
unprivileged clients, so there we fall back to the running-process signal
(``/proc/<pid>/environ``), which is display-server agnostic: if exactly one
*configured* game is running, we assume that's the one being played.
"""
from __future__ import annotations

import glob
import os
import re
import subprocess

_WIN_RE = re.compile(r"window id # (0x[0-9a-fA-F]+)")
_PID_RE = re.compile(r"=\s*(\d+)")


def parse_window_id(output: str) -> str | None:
    m = _WIN_RE.search(output)
    if not m:
        return None
    wid = m.group(1)
    return None if int(wid, 16) == 0 else wid


def parse_wm_pid(output: str) -> int | None:
    m = _PID_RE.search(output)
    return int(m.group(1)) if m else None


def appid_from_environ(environ: bytes) -> str | None:
    for entry in environ.split(b"\x00"):
        if entry.startswith(b"SteamAppId="):
            return entry.split(b"=", 1)[1].decode("utf-8", "replace")
    return None


def _read_environ(pid: int) -> bytes:
    try:
        with open(f"/proc/{pid}/environ", "rb") as fh:
            return fh.read()
    except OSError:
        return b""


def _proc_pids() -> list[int]:
    pids = []
    try:
        for name in os.listdir("/proc"):
            if name.isdigit():
                pids.append(int(name))
    except OSError:
        return []
    return pids


def running_appids(pids=None, read_environ=_read_environ) -> list[str]:
    """Distinct Steam AppIDs across running processes (order of first sight)."""
    if pids is None:
        pids = _proc_pids()
    seen: list[str] = []
    for pid in pids:
        try:
            environ = read_environ(pid)
        except OSError:
            continue
        appid = appid_from_environ(environ)
        if appid and appid not in seen:
            seen.append(appid)
    return seen


def current_appid(run=subprocess.run, read_environ=_read_environ) -> str | None:
    """Return the Steam AppID of the focused window's process, or None."""
    try:
        root = run(["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                   capture_output=True, text=True, timeout=2).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    wid = parse_window_id(root)
    if wid is None:
        return None
    try:
        win = run(["xprop", "-id", wid, "_NET_WM_PID"],
                  capture_output=True, text=True, timeout=2).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    pid = parse_wm_pid(win)
    if pid is None:
        return None
    return appid_from_environ(read_environ(pid))


def is_wayland(environ=None, runtime_dir=None) -> bool:
    """Whether the session is running under a Wayland compositor.

    Robust inside a systemd --user service, which does NOT inherit
    XDG_SESSION_TYPE/WAYLAND_DISPLAY: we also look for a ``wayland-*`` socket
    in XDG_RUNTIME_DIR, which is present whenever a Wayland compositor is up.
    """
    environ = os.environ if environ is None else environ
    if environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        return True
    if environ.get("WAYLAND_DISPLAY"):
        return True
    rd = runtime_dir or environ.get("XDG_RUNTIME_DIR")
    if rd:
        return any(glob.glob(os.path.join(rd, "wayland-*")))
    return False


def single_running_known_appid(known_appids, running=None) -> str | None:
    """The one running AppID that is also configured, else None.

    Returns None when zero or more than one configured game is running, so an
    ambiguous situation falls back to the default profile rather than guessing.
    """
    known = set(known_appids)
    if not known:
        return None
    running = running_appids() if running is None else running
    matches = [a for a in running if a in known]
    return matches[0] if len(matches) == 1 else None
