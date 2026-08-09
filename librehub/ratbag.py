"""Thin wrapper over the `ratbagctl` CLI (Layer 1 signal setup).

Backs the one-time mouse setup described in the README (assigning each
physical button a unique KEY_F13-KEY_F24 signal in the mouse's onboard
profile 0, and activating that profile). That step is currently manual;
this module is also the intended foundation for the planned guided
in-app first-run setup, so it is intentionally invoked by setup tooling
and documentation rather than by the GUI/daemon at runtime — do not
treat it as dead code.
"""
from __future__ import annotations

import re
import subprocess

MODEL_DEFAULT = "G502 HERO"


class RatbagError(Exception):
    pass


def _run(args, run):
    try:
        return run(args, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        raise RatbagError(f"failed to run {' '.join(args)}: {e}") from e


def resolve_device(model: str, run=subprocess.run) -> str | None:
    res = _run(["ratbagctl", "list"], run)
    for line in res.stdout.splitlines():
        if ":" not in line:
            continue
        short, _, desc = line.partition(":")
        if model.lower() in desc.lower():
            return short.strip()
    return None


_BTN_RE = re.compile(r"Button:\s+(\d+)\s+is mapped to (.+?)\s*$")


def parse_buttons(info_output: str) -> dict[int, str]:
    """Return {button_index: action_text} for the active profile."""
    result: dict[int, str] = {}
    in_active = False
    for line in info_output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Profile"):
            in_active = "(active)" in stripped
            continue
        if not in_active:
            continue
        m = _BTN_RE.search(line)
        if m:
            result[int(m.group(1))] = m.group(2).strip()
    return result


def assign_signal(dev: str, profile: int, button: int, fcode: str,
                  run=subprocess.run) -> None:
    res = _run(["ratbagctl", dev, "profile", str(profile), "button", str(button),
                "action", "set", "macro", fcode], run)
    if res.returncode != 0:
        raise RatbagError(f"assigning {fcode} to button {button} failed")


def set_active_profile(dev: str, profile: int, run=subprocess.run) -> None:
    res = _run(["ratbagctl", dev, "profile", "active", "set", str(profile)], run)
    if res.returncode != 0:
        raise RatbagError(f"setting active profile {profile} failed")
