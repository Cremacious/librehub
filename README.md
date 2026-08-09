# LibreHub

**Per-game mouse-button remapper for Linux** — the open answer to Logitech G HUB's per-game feature.

Assign gaming-mouse buttons to keyboard keys **per game**, switched automatically when a Steam game gets focus. No more manual remapping between titles.

---

## Why LibreHub?

Logitech G HUB does not run usefully on Linux. Its signature convenience — *different mouse-button-to-key mappings per game, applied automatically* — has no simple native equivalent:

- `input-remapper` remaps globally but lacks per-game switching
- `ratbagd`/Piper configure onboard profiles but cap at ~5 and require manual switching

**LibreHub** is a focused, Linux-native app that gives you unlimited per-game profiles with automatic switching by Steam AppID.

---

## Requirements

- **Mouse:** Logitech (or other `ratbagd`-supported) gaming mouse with programmable buttons
- **Display server:** X11 (Wayland support planned)
- **Platform:** Steam on Linux
- **Python:** 3.10 or later
- **System packages:**
  - `python3-gi` — Python GTK3 bindings
  - `gir1.2-gtk-3.0` — GTK3 introspection data
  - `libratbag-tools` — `ratbagctl` command-line utility
- **Python dependencies:** `evdev>=1.6` (installed automatically by the installer)

---

## Installation

```bash
./install.sh
```

**What it does:**
1. Installs LibreHub and `librehub-daemon` commands via `pip`
2. Installs a udev rule to allow the daemon to access `/dev/uinput` (requires `sudo`)
3. Adds your user to the `input` group (requires `sudo`)
4. Installs and enables the daemon as a systemd `--user` service

**Important:** After running `install.sh`, you must **log out and back in** for the `input` group membership to take effect. The daemon will start automatically on next login.

---

## Usage

### Add a Game & Configure Bindings

1. **Open LibreHub:**
   ```bash
   librehub
   ```

2. **Add a game** (click the Add button):
   - **Detect running game:** If you're already playing, LibreHub will detect the Steam AppID
   - **Enter AppID manually:** Find it at `steamdb.info` or from Steam's URL
   - The game will be added to your profiles list

3. **Configure button bindings:**
   - Select the game's profile
   - Click "Identify button" and press a mouse button → LibreHub shows which button you pressed
   - Click "Set key" and press the keyboard key you want it to send
   - Add more button-to-key mappings as needed
   - Click **Save**

### Auto-Switching

Once configured, LibreHub will:
- Monitor which game has keyboard focus (via Steam AppID)
- Automatically switch to that game's binding set when it launches
- Fall back to the `default` set when no mapped game is active
- Log unmapped games so you can discover and add them later

---

## How It Works

LibreHub uses a **two-layer architecture** for reliability and simplicity:

### Layer 1: Signal (Hardware via ratbagd)

Each managed mouse button is configured (via `ratbagctl`) to emit a unique, otherwise-unused F-key (`KEY_F13`…`KEY_F24`). These live in a single always-active onboard profile on the mouse itself, bypassing the 5-profile hardware ceiling. Standard clicks and wheel remain unaffected.

### Layer 2: Translation (Software Daemon)

The `librehub-daemon`:
1. Grabs the mouse's keyboard endpoint (where the F-codes arrive) exclusively
2. Creates a virtual `uinput` keyboard for output
3. Looks up the currently focused game's binding set (or the default)
4. Maps incoming F-codes to the configured keys and injects them
5. Watches `_NET_ACTIVE_WINDOW` (~500ms poll) to detect game focus changes

**Result:** no interception of pointer movement or clicks; the daemon only handles button-to-key translation.

---

## Limitations (v1)

- **One key per binding:** buttons map to single keys, not macros or modifier combos
- **Steam games only:** AppID matching; non-Steam games require manual setup (planned for v2)
- **Logitech/ratbagd mice only:** requires hardware that ratbagd supports (universal engine planned)
- **X11 only:** Wayland support planned

---

## Roadmap

- **v2:** Macros and modifier combinations (Ctrl+Q, multi-key sequences)
- **v2:** Non-Steam game matching (by window title, process name)
- **v3:** Universal mouse engine (support any mouse via full evdev remapping)
- **v3:** Wayland support

---

## Demo

(Demo GIF to be added)

---

## License

MIT License. See `LICENSE` for details.

---

## Troubleshooting

**Daemon not starting?**
```bash
systemctl --user status librehub-daemon.service
systemctl --user enable --now librehub-daemon.service
```

**Permission errors on `/dev/uinput`?**
- Confirm you're in the `input` group: `id -nG | grep input`
- If not listed, re-run `install.sh` and log out/in

**Mouse not detected?**
```bash
ratbagctl list
# or check systemd logs:
journalctl --user -u librehub-daemon.service -f
```

---

## Contributing

LibreHub is an open-source project. Bug reports, feature requests, and pull requests are welcome.

---

## Author

Chris — originally built to migrate fully off Windows to Linux Mint Cinnamon.
