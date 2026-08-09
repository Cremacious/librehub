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

from . import keys

MODEL_DEFAULT = "G502 HERO"


class RatbagError(Exception):
    pass


def _run(args, run):
    try:
        return run(args, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        raise RatbagError(f"failed to run {' '.join(args)}: {e}") from e


def resolve_device(model: str | None = None, run=subprocess.run) -> str | None:
    res = _run(["ratbagctl", "list"], run)
    if not model:
        for line in res.stdout.splitlines():
            if not line.strip():
                continue
            short, _, _desc = line.partition(":")
            return short.strip()
        return None
    for line in res.stdout.splitlines():
        if ":" not in line:
            continue
        short, _, desc = line.partition(":")
        if model.lower() in desc.lower():
            return short.strip()
    return None


def device_name(dev: str, run=subprocess.run) -> str | None:
    res = _run(["ratbagctl", dev, "name"], run)
    if res.returncode != 0:
        return None
    name = res.stdout.strip()
    return name or None


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


def device_info(dev: str, run=subprocess.run) -> str:
    """Return the stdout of `ratbagctl <dev> info`."""
    res = _run(["ratbagctl", dev, "info"], run)
    if res.returncode != 0:
        raise RatbagError(f"reading info for {dev} failed")
    return res.stdout


def parse_profile_buttons(info_output: str, profile: int) -> dict[int, str]:
    """Return {button_index: action_text} for the given profile number."""
    result: dict[int, str] = {}
    in_profile = False
    for line in info_output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Profile"):
            m = re.match(r"Profile\s+(\d+):", stripped)
            in_profile = bool(m) and int(m.group(1)) == profile
            continue
        if not in_profile:
            continue
        m = _BTN_RE.search(line)
        if m:
            result[int(m.group(1))] = m.group(2).strip()
    return result


def next_free_signals(used, count: int) -> list[str]:
    """Return the first `count` fcodes from keys.FSIGNALS not present in `used`."""
    used_set = set(used)
    free = [code for code in keys.FSIGNALS if code not in used_set]
    if len(free) < count:
        raise RatbagError(
            f"not enough free signals: need {count}, have {len(free)}"
        )
    return free[:count]


def signals_in_use(profile_buttons: dict[int, str]) -> set[str]:
    """Return the F-signals currently assigned to any button in the map.

    ratbagctl renders a KEY_F13 macro with the token after `KEY_` (e.g.
    `F13`) embedded in the action text, e.g. `macro '↕F13'`. We detect a
    signal by substring match of that token against each action text.
    """
    result: set[str] = set()
    for action in profile_buttons.values():
        for fcode in keys.FSIGNALS:
            token = fcode.removeprefix("KEY_")
            if token in action:
                result.add(fcode)
    return result


def plan_signal_assignment(
    previously_managed: dict[str, str], checked, reserved: set[str]
) -> tuple[dict[str, str], dict[int, str]]:
    """Plan fcode allocation for the checked buttons.

    `previously_managed` is the current {index_str: fcode} mapping,
    `checked` is the iterable of button indices the user checked, and
    `reserved` is the set of fcodes that must not be handed to a newly
    allocated button (e.g. signals live on the hardware but no longer
    tracked, or codes already in use by other managed buttons).

    Returns (final_managed, new_assignments):
      - final_managed: {str(index): fcode} for every checked index.
      - new_assignments: {index: fcode} for only the newly-allocated
        buttons (the ones needing a hardware assign_signal call).
    """
    checked = list(checked)
    kept: dict[int, str] = {}
    new_indices: list[int] = []
    for idx in checked:
        key = str(idx)
        if key in previously_managed:
            kept[idx] = previously_managed[key]
        else:
            new_indices.append(idx)

    used = set(reserved) | set(kept.values())
    new_codes = next_free_signals(used=used, count=len(new_indices))
    new_assignments = dict(zip(new_indices, new_codes))

    final_managed = {str(idx): fcode for idx, fcode in kept.items()}
    final_managed.update(
        {str(idx): fcode for idx, fcode in new_assignments.items()})
    return final_managed, new_assignments
