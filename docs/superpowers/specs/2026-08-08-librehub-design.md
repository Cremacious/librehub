# LibreHub — Design Spec

**Date:** 2026-08-08
**Status:** Approved for planning
**One-liner:** The open, Linux-native answer to Logitech G HUB's per-game feature — assign gaming-mouse buttons to keyboard keys **per game**, switched automatically when a Steam game gets focus.

---

## 1. Problem & Goal

Logitech G HUB does not run usefully on Linux, and its signature convenience — *different mouse-button-to-key mappings per game, applied automatically* — has no simple native equivalent. `input-remapper` can remap buttons but is general-purpose and has no per-application switching; `ratbagd`/Piper configure onboard profiles but cap at ~5 and switch manually.

**Goal:** a focused, game-centric app where a user can, on the fly, set up "for game X, these mouse buttons send these keys," add unlimited games with an easy GUI, and have the right mapping apply automatically the moment that game is focused.

**Primary user:** the author (Logitech G502 HERO, Linux Mint Cinnamon, X11), migrating fully off Windows. Publishable as open source for others with Logitech/ratbagd mice.

## 2. Non-Goals (v1)

Deliberately out of scope for the first release (tracked as roadmap):

- Macros, modifiers, or multi-key sequences per button (v1 = one key per button).
- Non-Steam game matching (v1 matches by Steam AppID only).
- Non-Logitech / non-`ratbagd` mice (v1 relies on the ratbagd signal layer).
- Wayland (v1 uses X11 active-window detection).
- Packaging beyond pip/pipx + install script (Flatpak/AUR later).

## 3. Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Engine | Logitech-tuned (ratbagd signal layer + software translation) | Avoids full-device evdev passthrough; simplest robust path; works on the target hardware today |
| Game matching | Steam AppID | Already built & tested; deterministic; covers the user's games |
| GUI toolkit | GTK3 / PyGObject | Native to Cinnamon, already installed, no heavy new dependency |
| Language | Python 3 | `python3-evdev` already present; fast to build; good GTK bindings |
| Display server | X11 | Cinnamon default; reliable `_NET_ACTIVE_WINDOW` detection |
| License | MIT | Permissive, standard for a small utility |

## 4. Architecture — Two Layers

### Layer 1 — Signal (hardware, via ratbagd, configured once by the app)

Each **managed** extra mouse button is set (through ratbagd) to emit a **unique, otherwise-unused key code from F13–F24** (Linux `KEY_F13`..`KEY_F24`, 12 available — more than any mouse's button count). These live in a single always-active onboard profile, so there is no 5-profile ceiling. Standard left/right/middle clicks are never reassigned.

Effect: every managed button is funneled onto the mouse's **keyboard endpoint** as a distinct F-code, while movement/wheel/clicks stay on the separate **pointer endpoint**.

### Layer 2 — Translation (software daemon)

The daemon:
1. Opens the mouse's keyboard endpoint (evdev) and **grabs it** (exclusive) so the raw F-codes never reach applications. This endpoint carries *only* the managed buttons, so grabbing it is safe and does not affect pointing/clicking.
2. Creates a virtual `uinput` keyboard for output.
3. Holds the **active binding set** (from config, selected by the focus-watcher).
4. On a managed button press/release, injects the mapped key down/up via `uinput`. Unmapped managed buttons are swallowed (no output).

Because Layer 1 isolates managed buttons onto one endpoint, the daemon **never intercepts or re-forwards pointer motion or clicks** — eliminating the most fragile part of a general evdev remapper.

### Auto-switcher (in the daemon)

Reuses the validated focus logic: poll `_NET_ACTIVE_WINDOW` (~0.5s) → window PID → read `SteamAppId` from `/proc/<pid>/environ` → look up the game's binding set → make it active. Falls back to the `default` set when no mapped game is focused. Unmapped focused Steam AppIDs are logged (so the GUI/user can discover them).

## 5. Components & Interfaces

Each is a focused module with a testable, mockable boundary:

- `config` — load/save/validate `config.json`; pure data model (`Game`, `Bindings`, `Config`). No I/O side effects beyond read/write. **Fully unit-tested.**
- `ratbag` — thin wrapper over `ratbagctl` (or ratbagd DBus): list device, resolve by model substring, read buttons, assign an F-code to a button. Behind an interface so tests mock it.
- `focus` (watcher) — X11 active window → Steam AppID. Pure extraction functions tested with fixtures; the polling loop is thin.
- `engine` — the evdev-grab + uinput-inject loop. Mapping decision (`(active_bindings, incoming_code) -> output_key | None`) is a **pure function**, unit-tested; the evdev/uinput I/O is a thin shell.
- `daemon` — wires focus + engine + config-reload (watches the config file; applies changes live). Entry point `librehub-daemon`.
- `gui` — GTK3 app (`librehub`). Reads/writes config via `config`; talks to the daemon over a small IPC (unix socket) for live button-detection and status.
- `ipc` — minimal unix-socket protocol: GUI ↔ daemon for "enter detect mode / here's the button you pressed" and "status/current game."

## 6. Config Format

`~/.config/librehub/config.json`:

```json
{
  "version": 1,
  "managed_buttons": { "6": "KEY_F13", "7": "KEY_F14", "5": "KEY_F15" },
  "games": {
    "1374490": { "name": "RuneScape: Dragonwilds",
                 "bindings": { "KEY_F13": "m", "KEY_F14": "f" } },
    "552500":  { "name": "Warhammer: Vermintide 2",
                 "bindings": { "KEY_F13": "4" } }
  },
  "default": { "bindings": {} }
}
```

- `managed_buttons` maps ratbag button index → assigned F-code (Layer 1 state).
- Each game's `bindings` maps F-code → output key.
- Daemon watches this file; edits from the GUI apply live.

## 7. GUI Flows

- **Profile list (left):** games + a `default` entry; **Add game** button.
- **Add game (3 paths):** ① *Detect the game I'm playing now* (query daemon for the current focused Steam AppID) — the on-the-fly path; ② pick from installed Steam library (parse `steamapps/appmanifest_*.acf` across library folders); ③ enter AppID manually.
- **Binding editor (right):** table of *[button] → [key]* rows. "Identify button" (press the physical button; daemon reports which F-code via IPC). "Set key" (press the desired key). Add/remove rows.
- **Status strip:** daemon up?, mouse detected?, active game.
- **First-run setup:** guided assignment of F-codes to the buttons the user wants to manage (writes Layer 1 via `ratbag`, populates `managed_buttons`).

## 8. Install & Permissions

- Distribution: `pipx install librehub` or `./install.sh`.
- One-time privileged setup (in `install.sh`): install a **udev rule** granting the `input` group read/write on `/dev/uinput`, and add the user to `input` (requires re-login). The daemon then runs **as the user**, no root.
- **systemd --user** unit `librehub-daemon.service` (WantedBy `graphical-session.target`) starts the daemon at login — replaces the interim `~/.local/bin/mouse-game-profile.sh` autostart.
- `.desktop` launcher for the GUI.

## 9. Error Handling

- Mouse/ratbagd absent → GUI warns and disables setup; daemon retries device discovery.
- ratbagd random short-name → resolve by model substring ("G502 HERO"); re-resolve on failure.
- Endpoint disappears (unplug) → daemon releases grab and re-acquires on replug.
- Invalid config → daemon keeps last-good, logs; GUI validates before save.
- Missing uinput permission → explicit error naming the fix (`install.sh` / re-login).
- Anti-cheat note: uinput injection is generally accepted (documented as a known caveat for EAC/BattlEye titles).

## 10. Testing Strategy

Built test-first where the logic is pure:

- `config`: load/save round-trip, validation, migration of `version`.
- `engine`: mapping function across mapped/unmapped/default cases.
- `focus`: AppID extraction from fixture `xprop`/environ data.
- `ratbag`: command construction verified against a mocked runner.
- Integration smoke: daemon applies the right binding set given a simulated focused AppID (mirrors the manual test already done with the shell prototype).
- GUI: manual/where feasible; core logic lives outside the GUI so it is covered by unit tests.

## 11. Repository Layout

```
librehub/
  librehub/            # package: config.py ratbag.py focus.py engine.py daemon.py gui.py ipc.py
  tests/
  packaging/           # librehub-daemon.service, 99-librehub-uinput.rules, librehub.desktop
  install.sh
  README.md            # with screenshot/GIF + setup
  LICENSE              # MIT
  pyproject.toml
  docs/superpowers/specs/2026-08-08-librehub-design.md
```

## 12. Milestones (for the implementation plan)

1. Core (test-first): `config`, `engine` mapping fn, `focus` extraction, `ratbag` wrapper.
2. Daemon: wire focus + engine + live config reload; ship as CLI; validate against real games.
3. Permissions/service: udev rule, input group, systemd --user unit, `install.sh`.
4. GUI: profile list + binding editor + add-game (detect/library/manual) + first-run setup + IPC detect.
5. Publish: README (with GIF), LICENSE, pyproject, `.desktop`; push to GitHub.
