# LibreHub Guided Mouse Setup — Plan Addendum

> Follow-on to `2026-08-08-librehub.md`. Adds the in-app first-run mouse setup the spec called for, so users never hand-run `ratbagctl`. Approach chosen with the user: **pick specific buttons** (list remappable buttons with current-action hints; user checks which to manage).

**Goal:** A "Set up mouse" GUI flow that assigns chosen mouse buttons unique `KEY_F13`–`KEY_F24` signals via `ratbagd` and records them in `managed_buttons`, so the existing press-to-detect binding flow works without manual `ratbagctl`.

## Global Constraints (inherited)
Python 3.10+; `ratbagctl` via injectable `run`; signals `KEY_F13`–`KEY_F24`; GUI is GTK3/PyGObject (manual-verified, no unit tests); real pytest at `.venv/bin/python -m pytest`; changes remain on branch `feat/librehub-mvp`.

---

### Task 13: `ratbag.py` guided-setup helpers (TDD)

**Files:** Modify `librehub/ratbag.py`; add tests to `tests/test_ratbag.py`.

**Interfaces produced:**
- `device_info(dev: str, run=subprocess.run) -> str` — stdout of `ratbagctl <dev> info` (raises `RatbagError` on failure).
- `parse_profile_buttons(info_output: str, profile: int) -> dict[int, str]` — `{button_index: action_text}` for the given profile number (NOT only the active one). Reuses the existing button-line regex; tracks the `Profile <n>:` section boundaries.
- `next_free_signals(used, count: int) -> list[str]` — the first `count` codes from `keys.FSIGNALS` not present in `used` (any iterable of fcode strings). Raises `RatbagError` if fewer than `count` remain.

**TDD tests (write first, confirm RED, then implement):**
- `parse_profile_buttons` on a multi-profile fixture returns profile 0's buttons and profile 1's buttons distinctly (e.g. profile 0 button 6 vs profile 1 button 6 differ).
- `parse_profile_buttons` returns `{}` for a profile index not present.
- `next_free_signals([], 3)` → `["KEY_F13","KEY_F14","KEY_F15"]`.
- `next_free_signals(["KEY_F13"], 2)` → `["KEY_F14","KEY_F15"]`.
- `next_free_signals` raises `RatbagError` when asked for more than remain (e.g. used = all 12, count 1).
- `device_info` builds `["ratbagctl", dev, "info"]` (verify via FakeRun) and returns its stdout.

**Commit:** `feat: add ratbag helpers for guided mouse setup`.

---

### Task 14: GUI "Set up mouse" dialog (manual-verified)

**Files:** Modify `librehub/gui.py` (add `from . import ratbag`).

**Behavior:**
- A **"Set up mouse"** button in the left pane.
- Handler resolves the device via `ratbag.resolve_device(ratbag.MODEL_DEFAULT)`; on `None` (or `RatbagError`) shows an error dialog and stops.
- Reads `ratbag.device_info(dev)` → `ratbag.parse_profile_buttons(info, 0)`. Builds a dialog listing each remappable button (EXCLUDE primary buttons — indices whose action is `button 1`/`button 2`/`button 3`) as a checkbox row: label `Button <index> — currently <action_text>`; pre-check indices already in `self.config.managed_buttons`.
- On OK: the checked indices are the managed set. Preserve existing fcodes for already-managed checked buttons; allocate new ones for newly-checked buttons via `ratbag.next_free_signals(used=<existing fcodes being kept>, count=<new count>)`. For each newly-assigned button call `ratbag.assign_signal(dev, 0, index, fcode)`. Then `ratbag.set_active_profile(dev, 0)`. Set `self.config.managed_buttons = {str(index): fcode}` for the checked set and `C.save(...)`.
- On any `RatbagError`, show an error dialog and do not partially persist (persist config only after hardware assignment succeeds).
- After success: info dialog stating the mouse is set up and the daemon must pick up the change; offer a **"Restart daemon"** action that runs `systemctl --user restart librehub-daemon` (via `subprocess.run`, non-fatal if it fails — show the outcome), or instructs the user to restart it.

**Manual verification (no GTK unit tests):**
- `.venv/bin/python -c "import librehub.gui"` and headless `Window()` construct/destroy (no `Gtk.main()`).
- Full suite `.venv/bin/python -m pytest` stays green.

**Commit:** `feat: add guided 'Set up mouse' dialog to the GUI`.

---

### Task 15: README + roadmap update

**Files:** Modify `README.md`.
- Replace the manual `ratbactl` one-time-setup section's framing: document the in-app **Set up mouse** flow as the primary path; keep the manual `ratbactl` commands as an "Advanced / manual alternative".
- Move "Guided in-app first-run mouse setup" from Roadmap to a shipped feature.
- Run full suite (docs-only, but confirm green). **Commit:** `docs: document guided mouse setup`.
