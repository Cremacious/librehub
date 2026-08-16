from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

_DEFAULTS = {
    "keep_above": True,
    "start_at_login": True,
    "tray_icon": False,
    "appearance": "system",
}


@dataclass
class Prefs:
    keep_above: bool = True
    start_at_login: bool = True
    tray_icon: bool = False
    appearance: str = "system"


def prefs_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "librehub" / "prefs.json"


def load(path: Path | None = None) -> Prefs:
    path = path or prefs_path()
    data = dict(_DEFAULTS)
    try:
        raw = json.loads(Path(path).read_text())
        if isinstance(raw, dict):
            for k in _DEFAULTS:
                if k in raw:
                    data[k] = raw[k]
    except (OSError, json.JSONDecodeError):
        pass
    if data["appearance"] not in ("system", "light", "dark"):
        data["appearance"] = "system"
    return Prefs(**data)


def save(prefs: Prefs, path: Path | None = None) -> None:
    path = path or prefs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(asdict(prefs), indent=2))
    os.replace(tmp, path)
