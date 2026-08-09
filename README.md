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

### One-time mouse setup

LibreHub's Layer 1 (see [How It Works](#how-it-works)) requires each mouse button you want to use to emit a unique signal, `KEY_F13`–`KEY_F24`, stored in the mouse's always-on onboard profile. **LibreHub now provides a guided in-app setup dialog** that automates this for you:

1. **Launch the GUI:**
   ```bash
   librehub
   ```

2. **Click "Set up mouse"** in the left pane.
   - LibreHub scans your mouse and shows a dialog listing each remappable button with its current action
   - Check the boxes next to the buttons you want to manage (LibreHub will exclude primary clicks: buttons 1, 2, 3)

3. **Click OK** to confirm.
   - LibreHub assigns each checked button a unique F-signal (`KEY_F13`–`KEY_F24`), programs them into your mouse's profile 0, and activates that profile
   - An info dialog appears confirming the setup is complete

4. **Restart the daemon** (if prompted).
   - Click "Restart daemon" in the dialog, or run:
     ```bash
     systemctl --user restart librehub-daemon
     ```

After this one-time setup, LibreHub's **"Add binding (press a mouse button)"** flow will detect those buttons.

#### Advanced: manual setup via ratbagctl

If you prefer to configure buttons manually or your mouse is not fully supported by the GUI, you can use `ratbagctl` directly:

1. **Find your device's short-name:**
   ```bash
   ratbagctl list
   ```

2. **Look up your button indices:**
   ```bash
   ratbagctl "<device>" info
   ```
   Note the button *indices* for the physical buttons you want to remap (e.g., the two thumb buttons might be indices `6` and `7`).

3. **Assign each button a unique F-signal in profile 0**, e.g.:
   ```bash
   ratbagctl "<device>" profile 0 button 6 action set macro KEY_F13
   ratbagctl "<device>" profile 0 button 7 action set macro KEY_F14
   ```
   Use a different F-code (`KEY_F13`…`KEY_F24`) for each button you assign — one per profile-0 button, no repeats.

4. **Make sure profile 0 is active:**
   ```bash
   ratbagctl "<device>" profile active set 0
   ```

### Start the Daemon

The daemon must be running for button detection and auto-switching to work:

```bash
# Already running as a systemd --user service from install.sh
# If needed, start it manually:
librehub-daemon
```

### Configure a Game

1. **Launch the GUI:**
   ```bash
   librehub
   ```
   The window shows a game list on the left and a bindings table on the right.

2. **Add the game:**
   - **Detect:** While the Steam game is running and focused, click **"Add game I'm playing now"** → the daemon detects the focused game and adds it
   - **Manual:** Click **"Add by AppID…"**, enter the Steam AppID (find it at `steamdb.info`), and click OK
   - The game now appears in the left list

3. **Select the game** in the left list to edit its bindings

4. **Add a binding:**
   - Click **"Add binding (press a mouse button)"**
   - Press the physical mouse button you want to bind
   - A new row appears showing the button signal (e.g., `KEY_F13`)

5. **Set the output key:**
   - Click the **"Key"** cell in that row
   - Type the key you want it to send (e.g., `m`, `4`, `space`, `q`)
   - Press Enter to confirm

6. **Repeat** for more buttons, then click **"Save"** to write the config

### Auto-Switching

Once a game is configured, LibreHub's daemon will:
- Monitor which game has keyboard focus (via Steam AppID)
- Automatically activate that game's bindings when it launches
- Fall back to the `default` bindings when no mapped game is focused
- Report unmapped games in systemd logs so you can discover and add them

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

### Known limitations

- **No hot-plug rediscovery:** the daemon discovers the mouse at startup only — if you plug/unplug the mouse during a session, restart the daemon with `systemctl --user restart librehub-daemon`

---

## Roadmap

- **v2:** Mouse hot-plug rediscovery
- **v2:** Macros and modifier combinations (Ctrl+Q, multi-key sequences)
- **v2:** Non-Steam game matching (by window title, process name)
- **v3:** Universal mouse engine (support any mouse via full evdev remapping)
- **v3:** Wayland support

**Recently shipped:**
- Guided in-app mouse setup ("Set up mouse" dialog auto-assigns F13–F24 via `ratbagd`)

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
