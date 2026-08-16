import re

from evdev import ecodes

FSIGNALS = [f"KEY_F{n}" for n in range(13, 25)]

_ALIASES = {
    "space": "KEY_SPACE",
    "spacebar": "KEY_SPACE",
    "enter": "KEY_ENTER",
    "return": "KEY_ENTER",
    "esc": "KEY_ESC",
    "escape": "KEY_ESC",
    "tab": "KEY_TAB",
    "backspace": "KEY_BACKSPACE",
    "bksp": "KEY_BACKSPACE",
    "delete": "KEY_DELETE",
    "del": "KEY_DELETE",
    "insert": "KEY_INSERT",
    "ins": "KEY_INSERT",
    "home": "KEY_HOME",
    "end": "KEY_END",
    "pageup": "KEY_PAGEUP",
    "pgup": "KEY_PAGEUP",
    "pagedown": "KEY_PAGEDOWN",
    "pgdn": "KEY_PAGEDOWN",
    "capslock": "KEY_CAPSLOCK",
    "ctrl": "KEY_LEFTCTRL",
    "control": "KEY_LEFTCTRL",
    "shift": "KEY_LEFTSHIFT",
    "alt": "KEY_LEFTALT",
    "up": "KEY_UP",
    "down": "KEY_DOWN",
    "left": "KEY_LEFT",
    "right": "KEY_RIGHT",
}

EXAMPLES = "e.g. r, 4, space, enter, esc, tab, shift, f1, up"

_FKEY_RE = re.compile(r"[fF](\d{1,2})")


def to_code(name: str) -> int:
    raw = name.strip()
    if not raw:
        raise ValueError("empty key name")
    fmatch = _FKEY_RE.fullmatch(raw)
    if raw.upper().startswith("KEY_"):
        key = raw.upper()
    elif raw.lower() in _ALIASES:
        key = _ALIASES[raw.lower()]
    elif fmatch and 1 <= int(fmatch.group(1)) <= 24:
        key = f"KEY_F{int(fmatch.group(1))}"
    elif len(raw) == 1:
        key = f"KEY_{raw.upper()}"
    else:
        raise ValueError(f"unknown key name: {name!r} ({EXAMPLES})")
    code = ecodes.ecodes.get(key)
    if code is None:
        raise ValueError(f"unknown key name: {name!r} (resolved {key})")
    return code
