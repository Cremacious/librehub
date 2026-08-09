"""Translate human key names to evdev key codes."""
from evdev import ecodes

FSIGNALS = [f"KEY_F{n}" for n in range(13, 25)]  # KEY_F13 .. KEY_F24

_ALIASES = {
    "space": "KEY_SPACE",
    "enter": "KEY_ENTER",
    "return": "KEY_ENTER",
    "esc": "KEY_ESC",
    "escape": "KEY_ESC",
    "tab": "KEY_TAB",
    "ctrl": "KEY_LEFTCTRL",
    "shift": "KEY_LEFTSHIFT",
    "alt": "KEY_LEFTALT",
    "up": "KEY_UP",
    "down": "KEY_DOWN",
    "left": "KEY_LEFT",
    "right": "KEY_RIGHT",
}


def to_code(name: str) -> int:
    """Return the evdev key code for a user key name, or raise ValueError."""
    raw = name.strip()
    if not raw:
        raise ValueError("empty key name")
    key = raw.upper() if raw.upper().startswith("KEY_") else _ALIASES.get(raw.lower())
    if key is None:
        # single character: letter or digit
        if len(raw) == 1:
            key = f"KEY_{raw.upper()}"
        else:
            raise ValueError(f"unknown key name: {name!r}")
    code = ecodes.ecodes.get(key)
    if code is None:
        raise ValueError(f"unknown key name: {name!r} (resolved {key})")
    return code
