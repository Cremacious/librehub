"""GTK3 editor for LibreHub per-game mouse bindings."""
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from . import config as C  # noqa: E402
from . import focus, ipc, keys, preflight, ratbag  # noqa: E402

_STATUS_ICON = {
    preflight.Status.OK: "✅",
    preflight.Status.WARN: "⚠️",
    preflight.Status.FAIL: "❌",
}

# ratbagctl reports these quoted, e.g. "'button 1'" (see parse_profile_buttons).
_PRIMARY_BUTTON_ACTIONS = {"'button 1'", "'button 2'", "'button 3'"}

_MANIFEST_NAME_RE = re.compile(r'"name"\s+"([^"]*)"')

# GDK keyval -> canonical key name understood by keys.to_code.
_GDK_SPECIAL = {
    Gdk.KEY_space: "space",
    Gdk.KEY_Return: "enter",
    Gdk.KEY_KP_Enter: "enter",
    Gdk.KEY_Escape: "esc",
    Gdk.KEY_Tab: "tab",
    Gdk.KEY_BackSpace: "backspace",
    Gdk.KEY_Delete: "delete",
    Gdk.KEY_Insert: "insert",
    Gdk.KEY_Home: "home",
    Gdk.KEY_End: "end",
    Gdk.KEY_Page_Up: "pageup",
    Gdk.KEY_Page_Down: "pagedown",
    Gdk.KEY_Up: "up",
    Gdk.KEY_Down: "down",
    Gdk.KEY_Left: "left",
    Gdk.KEY_Right: "right",
    Gdk.KEY_Shift_L: "shift",
    Gdk.KEY_Shift_R: "shift",
    Gdk.KEY_Control_L: "ctrl",
    Gdk.KEY_Control_R: "ctrl",
    Gdk.KEY_Alt_L: "alt",
    Gdk.KEY_Alt_R: "alt",
    Gdk.KEY_Caps_Lock: "capslock",
}

_PRETTY = {
    "space": "Spacebar", "esc": "Esc", "enter": "Enter", "tab": "Tab",
    "backspace": "Backspace", "delete": "Delete", "insert": "Insert",
    "home": "Home", "end": "End", "pageup": "Page Up", "pagedown": "Page Down",
    "capslock": "Caps Lock", "shift": "Shift", "ctrl": "Ctrl", "alt": "Alt",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
}


def key_name_from_keyval(keyval: int) -> str | None:
    """Translate a GDK keyval (from a key-press) into a canonical key name
    that keys.to_code accepts, or None if unsupported."""
    if keyval in _GDK_SPECIAL:
        return _GDK_SPECIAL[keyval]
    if Gdk.KEY_F1 <= keyval <= Gdk.KEY_F24:
        return f"f{keyval - Gdk.KEY_F1 + 1}"
    uni = Gdk.keyval_to_unicode(keyval)
    if uni:
        ch = chr(uni)
        if len(ch) == 1 and ch.isprintable() and not ch.isspace():
            name = ch.lower()
            try:
                keys.to_code(name)
            except ValueError:
                return None
            return name
    return None


def pretty_key(name: str) -> str:
    """Human-friendly label for a stored key name."""
    if name in _PRETTY:
        return _PRETTY[name]
    if re.fullmatch(r"f\d{1,2}", name):
        return name.upper()
    return name.upper() if len(name) == 1 else name.capitalize()


_LIBRARY_PATH_RE = re.compile(r'"path"\s+"([^"]+)"')


def _steam_roots() -> list[Path]:
    home = Path.home()
    return [
        home / ".steam" / "steam",
        home / ".steam" / "root",
        home / ".steam" / "debian-installation",
        home / ".local" / "share" / "Steam",
    ]


def parse_library_paths(vdf_text: str) -> list[str]:
    """Extract Steam library base paths from a libraryfolders.vdf body."""
    return _LIBRARY_PATH_RE.findall(vdf_text)


def _steamapps_dirs() -> list[Path]:
    """Every steamapps dir Steam knows about, incl. extra library folders."""
    dirs: list[Path] = []
    seen: set[Path] = set()

    def add(sa: Path):
        if sa not in seen:
            seen.add(sa)
            dirs.append(sa)

    for root in _steam_roots():
        sa = root / "steamapps"
        add(sa)
        try:
            text = (sa / "libraryfolders.vdf").read_text(errors="replace")
        except OSError:
            continue
        for base in parse_library_paths(text):
            add(Path(base) / "steamapps")
    return dirs


def _steam_manifest_paths(appid: str) -> list[Path]:
    return [d / f"appmanifest_{appid}.acf" for d in _steamapps_dirs()]


def _resolve_game_name(appid: str) -> str:
    """Best-effort display name for a Steam AppID from local manifests."""
    for path in _steam_manifest_paths(appid):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        m = _MANIFEST_NAME_RE.search(text)
        if m:
            return m.group(1)
    return f"Game {appid}"


def _ipc_request(msg: dict, timeout: float = 11) -> dict | None:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(ipc.socket_path())
        s.sendall(ipc.encode(msg))
        data = s.makefile("rb").readline()
        s.close()
        return ipc.decode(data)
    except (OSError, ValueError):
        return None


class Window(Gtk.Window):
    def __init__(self):
        super().__init__(title="LibreHub")
        self.set_default_size(760, 480)
        # Float above other windows so the editor can be summoned over a
        # (borderless) fullscreen game instead of hiding behind it.
        self.set_keep_above(True)
        self.cfg_path = C.config_path()
        self._first_run = not self.cfg_path.exists()
        self._editing: str | None = None
        self._config_warning: str | None = None
        try:
            self.config = C.load(self.cfg_path)
        except C.ConfigError as e:
            self.config = C.default_config()
            if self.cfg_path.exists():
                backup = self.cfg_path.with_suffix(self.cfg_path.suffix + ".bak")
                try:
                    os.replace(self.cfg_path, backup)
                    self._config_warning = (
                        f"Could not read {self.cfg_path}: {e}\n"
                        f"The unreadable file was backed up to {backup.name}; "
                        "starting from a fresh default config."
                    )
                except OSError as backup_err:
                    self._config_warning = (
                        f"Could not read {self.cfg_path}: {e}\n"
                        f"Also failed to back it up: {backup_err}. "
                        "Starting from a fresh default config; saving may "
                        "overwrite the unreadable file."
                    )
            # else: no config file yet (first run) — nothing to warn about.

        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add(outer)

        # left: game list + add/remove/setup
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.game_store = Gtk.ListStore(str, str)  # appid, label
        self.game_view = Gtk.TreeView(model=self.game_store)
        self.game_view.append_column(
            Gtk.TreeViewColumn("Game", Gtk.CellRendererText(), text=1))
        self.game_view.get_selection().connect("changed", self._on_game_selected)
        left.pack_start(self.game_view, True, True, 0)
        add_btn = Gtk.Button(label="Add game I'm playing now")
        add_btn.connect("clicked", self._on_add_current)
        left.pack_start(add_btn, False, False, 0)
        add_manual = Gtk.Button(label="Add by AppID…")
        add_manual.connect("clicked", self._on_add_manual)
        left.pack_start(add_manual, False, False, 0)
        rename_game_btn = Gtk.Button(label="Rename selected game")
        rename_game_btn.connect("clicked", self._on_rename_game)
        left.pack_start(rename_game_btn, False, False, 0)
        remove_game_btn = Gtk.Button(label="Remove selected game")
        remove_game_btn.connect("clicked", self._on_remove_game)
        left.pack_start(remove_game_btn, False, False, 0)
        setup_mouse_btn = Gtk.Button(label="Set up mouse")
        setup_mouse_btn.connect("clicked", self._on_setup_mouse)
        left.pack_start(setup_mouse_btn, False, False, 0)
        health_btn = Gtk.Button(label="Setup / Health check")
        health_btn.connect("clicked", lambda _b: self._open_setup_dialog())
        left.pack_start(health_btn, False, False, 0)
        outer.pack_start(left, False, False, 0)

        # right: bindings for the selected profile
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.profile_label = Gtk.Label(label="Select a game or the default profile")
        self.profile_label.set_xalign(0)
        right.pack_start(self.profile_label, False, False, 0)
        # bind_store: (fcode, canonical key name, pretty label)
        self.bind_store = Gtk.ListStore(str, str, str)
        self.bind_view = Gtk.TreeView(model=self.bind_store)
        self.bind_view.append_column(
            Gtk.TreeViewColumn("Mouse button", Gtk.CellRendererText(), text=0))
        self.bind_view.append_column(
            Gtk.TreeViewColumn("Sends key", Gtk.CellRendererText(), text=2))
        right.pack_start(self.bind_view, True, True, 0)
        add_bind_btn = Gtk.Button(label="Add keybinding")
        add_bind_btn.connect("clicked", self._on_add_keybinding)
        right.pack_start(add_bind_btn, False, False, 0)
        remove_bind_btn = Gtk.Button(label="Remove selected keybinding")
        remove_bind_btn.connect("clicked", self._on_remove_binding)
        right.pack_start(remove_bind_btn, False, False, 0)
        self.status = Gtk.Label(label="")
        self.status.set_xalign(0)
        right.pack_start(self.status, False, False, 0)
        outer.pack_start(right, True, True, 0)

        self._refresh_games()
        self._refresh_status()
        # Re-poll status so a daemon that comes up (or goes down) later is
        # reflected without reopening the window — the one-shot check at launch
        # used to latch onto a stale "not running" during daemon startup.
        GLib.timeout_add_seconds(2, self._poll_status)
        # Guide the user through anything that still needs doing.
        GLib.idle_add(self._maybe_autoshow_setup)
        if self._config_warning:
            self.status.set_text(
                f"config error, backed up to .bak — {self.status.get_text()}")
            self.connect("show", lambda *_a: self._error(self._config_warning))

    # --- helpers ---
    def _refresh_games(self):
        self.game_store.clear()
        self.game_store.append(["", "(default)"])
        for aid, g in self.config.games.items():
            self.game_store.append([aid, f"{g.name} [{aid}]"])

    def _refresh_status(self):
        st = _ipc_request({"cmd": "status"}, timeout=1.5)
        if st and st.get("daemon"):
            if st.get("remapping"):
                self.status.set_text(
                    f"daemon: running · device: {st.get('device')} · "
                    f"active: {st.get('active_appid') or 'default'}")
            else:
                self.status.set_text(
                    "daemon: running, but remapping is inactive — "
                    "open Setup / Health check")
        else:
            self.status.set_text(
                "daemon: not running — open Setup / Health check")

    def _poll_status(self) -> bool:
        self._refresh_status()
        return True  # keep the GLib timer alive

    def _maybe_autoshow_setup(self) -> bool:
        checks = preflight.run_all(self.config.managed_buttons)
        _surface = {preflight.FIX_RELOGIN, preflight.FIX_RESTART_DAEMON}
        actionable = any(
            c.status is preflight.Status.FAIL or c.fix in _surface
            for c in checks)
        if self._first_run or actionable:
            self._open_setup_dialog(checks=checks)
        return False  # run once

    def _current_profile(self) -> C.Game | None:
        """The Game object for the current game-list selection (the default
        profile for the '(default)' row), or None if nothing is selected."""
        model, it = self.game_view.get_selection().get_selected()
        if it is None:
            return None
        aid = model[it][0]
        self._editing = aid or None
        return self.config.default if not aid else self.config.games.get(aid)

    def _refresh_bindings(self):
        self.bind_store.clear()
        game = self._current_profile()
        if game is None:
            self.profile_label.set_text("Select a game or the default profile")
            return
        label = "default profile" if not self._editing else f"{game.name}"
        self.profile_label.set_text(f"Keybindings for {label}")
        for fcode, name in game.bindings.items():
            self.bind_store.append([fcode, name, pretty_key(name)])

    def _persist(self) -> bool:
        try:
            C.save(self.config, self.cfg_path)
            return True
        except OSError as e:
            self._error(f"save failed: {e}")
            return False

    def _on_game_selected(self, _sel):
        self._refresh_bindings()

    # --- add keybinding: press mouse button, then press key, auto-save ---
    def _on_add_keybinding(self, _btn):
        game = self._current_profile()
        if game is None:
            self._error("Select a game (or the default profile) first.")
            return
        fcode = self._detect_button()
        if fcode is None:
            return
        name = self._capture_key()
        if name is None:
            return
        game.bindings[fcode] = name
        if self._persist():
            self._refresh_bindings()
            self.status.set_text(f"bound that button to {pretty_key(name)}.")

    def _detect_button(self) -> str | None:
        # The daemon blocks up to ~10s waiting for a button press, so the IPC
        # call runs in a worker thread — otherwise it would freeze the main
        # loop and the "press now" popup would never paint.
        dlg = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.CANCEL,
            text="Press a mouse button now")
        dlg.format_secondary_text(
            "Press the physical mouse button you want to bind. "
            "Waiting up to 10 seconds…")
        state = {"alive": True, "resp": None}

        def work():
            resp = _ipc_request({"cmd": "detect"})
            GLib.idle_add(on_result, resp)

        def on_result(resp):
            if not state["alive"]:
                return False
            state["resp"] = resp
            dlg.response(Gtk.ResponseType.OK)  # button detected — close popup
            return False

        threading.Thread(target=work, daemon=True).start()
        response = dlg.run()
        state["alive"] = False
        dlg.destroy()
        if response != Gtk.ResponseType.OK:
            return None  # user cancelled
        fcode = (state["resp"] or {}).get("fcode")
        if not fcode:
            self._error(
                "No button detected within the time limit. Make sure the "
                "daemon is running (see Setup / Health check) and that you've "
                "run 'Set up mouse' to assign the buttons first, then try "
                "again.")
            return None
        return fcode

    def _capture_key(self) -> str | None:
        dlg = Gtk.Dialog(title="Assign key", transient_for=self, modal=True)
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        lbl = Gtk.Label(label="Now press the key you want this button to send…")
        dlg.get_content_area().add(lbl)
        holder: dict[str, str] = {}

        def on_key(_w, event):
            name = key_name_from_keyval(event.keyval)
            if name is None:
                lbl.set_text("Unsupported key — try a letter, number, space, "
                             "enter, an f-key, or an arrow…")
                return True
            holder["name"] = name
            dlg.response(Gtk.ResponseType.OK)
            return True

        dlg.connect("key-press-event", on_key)
        dlg.show_all()
        resp = dlg.run()
        dlg.destroy()
        if resp == Gtk.ResponseType.OK:
            return holder.get("name")
        return None

    def _on_remove_binding(self, _btn):
        game = self._current_profile()
        if game is None:
            self._error("Select a game or the default profile first.")
            return
        model, it = self.bind_view.get_selection().get_selected()
        if it is None:
            self._error("Select a keybinding row to remove.")
            return
        fcode = model[it][0]
        game.bindings.pop(fcode, None)
        if self._persist():
            self._refresh_bindings()
            self.status.set_text("keybinding removed.")

    def _on_add_current(self, _btn):
        appids = focus.running_appids()
        if not appids:
            self._error(
                "No running Steam game detected. Launch the game (through "
                "Steam) and try again. Non-Steam games can be added with "
                "'Add by AppID…'.")
            return
        if len(appids) == 1:
            aid = appids[0]
        else:
            aid = self._choose_running_game(appids)
            if aid is None:
                return
        self.config.games.setdefault(
            aid, C.Game(name=_resolve_game_name(aid), bindings={}))
        if self._persist():
            self._refresh_games()
            self._select_game_row(aid)

    def _choose_running_game(self, appids: list[str]) -> str | None:
        dlg = Gtk.Dialog(title="Choose a running game", transient_for=self,
                         modal=True)
        dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                        Gtk.STOCK_OK, Gtk.ResponseType.OK)
        content = dlg.get_content_area()
        radios: dict[str, Gtk.RadioButton] = {}
        group = None
        for aid in appids:
            label = f"{_resolve_game_name(aid)} [{aid}]"
            rb = Gtk.RadioButton.new_with_label_from_widget(group, label)
            group = group or rb
            content.add(rb)
            radios[aid] = rb
        dlg.show_all()
        response = dlg.run()
        chosen = None
        if response == Gtk.ResponseType.OK:
            for aid, rb in radios.items():
                if rb.get_active():
                    chosen = aid
                    break
        dlg.destroy()
        return chosen

    def _select_game_row(self, appid: str):
        it = self.game_store.get_iter_first()
        while it is not None:
            if self.game_store[it][0] == appid:
                self.game_view.get_selection().select_iter(it)
                break
            it = self.game_store.iter_next(it)

    def _on_add_manual(self, _btn):
        dlg = Gtk.Dialog(title="Add by AppID", transient_for=self, modal=True)
        dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                        Gtk.STOCK_OK, Gtk.ResponseType.OK)
        entry = Gtk.Entry()
        entry.set_placeholder_text("Steam AppID, e.g. 552500")
        dlg.get_content_area().add(entry)
        dlg.show_all()
        if dlg.run() == Gtk.ResponseType.OK:
            aid = entry.get_text().strip()
            if aid.isdigit():
                self.config.games.setdefault(
                    aid, C.Game(name=_resolve_game_name(aid), bindings={}))
                if self._persist():
                    self._refresh_games()
                    self._select_game_row(aid)
        dlg.destroy()

    def _on_rename_game(self, _btn):
        model, it = self.game_view.get_selection().get_selected()
        if it is None or not model[it][0]:
            self._error("Select a game to rename. The default profile "
                        "can't be renamed.")
            return
        aid = model[it][0]
        game = self.config.games.get(aid)
        if game is None:
            return
        dlg = Gtk.Dialog(title="Rename game", transient_for=self, modal=True)
        dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                        Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.OK)
        content = dlg.get_content_area()
        content.add(Gtk.Label(label=f"New name for AppID {aid}:"))
        entry = Gtk.Entry()
        entry.set_text(game.name)
        entry.set_activates_default(True)  # Enter confirms
        content.add(entry)
        dlg.show_all()
        confirmed = dlg.run() == Gtk.ResponseType.OK
        new_name = entry.get_text().strip()
        dlg.destroy()
        if not confirmed or not new_name or new_name == game.name:
            return
        game.name = new_name
        if self._persist():
            self._refresh_games()
            self._select_game_row(aid)
            self.status.set_text(f"renamed to {new_name}.")

    def _on_remove_game(self, _btn):
        model, it = self.game_view.get_selection().get_selected()
        if it is None or not model[it][0]:
            self._error("Select a game to remove. The default profile "
                        "can't be removed.")
            return
        aid = model[it][0]
        game = self.config.games.get(aid)
        name = game.name if game else aid
        confirm = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"Remove '{name}' [{aid}]?")
        confirm.format_secondary_text(
            "This deletes its bindings from LibreHub. (It does not change "
            "the mouse's onboard button signals.)")
        response = confirm.run()
        confirm.destroy()
        if response != Gtk.ResponseType.OK:
            return
        self.config.games.pop(aid, None)
        self._editing = None
        self.bind_store.clear()
        self.profile_label.set_text("Select a game or the default profile")
        if not self._persist():
            return
        selection = self.game_view.get_selection()
        selection.handler_block_by_func(self._on_game_selected)
        self._refresh_games()
        selection.handler_unblock_by_func(self._on_game_selected)
        self.status.set_text(f"removed {name}.")

    def _on_setup_mouse(self, _btn):
        try:
            dev = ratbag.resolve_device()
        except ratbag.RatbagError as e:
            self._error(f"could not detect mouse: {e}")
            return
        if not dev:
            self._error("No supported mouse found.")
            return

        try:
            info = ratbag.device_info(dev)
        except ratbag.RatbagError as e:
            self._error(f"could not read mouse info: {e}")
            return

        buttons = ratbag.parse_profile_buttons(info, 0)
        remappable = {idx: action for idx, action in buttons.items()
                      if action not in _PRIMARY_BUTTON_ACTIONS}
        if not remappable:
            self._error("No remappable buttons found on this mouse.")
            return

        dlg = Gtk.Dialog(title="Set up mouse", transient_for=self, modal=True)
        dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                        Gtk.STOCK_OK, Gtk.ResponseType.OK)
        content = dlg.get_content_area()
        checks: dict[int, Gtk.CheckButton] = {}
        for idx in sorted(remappable):
            cb = Gtk.CheckButton(
                label=f"Button {idx} — currently {remappable[idx]}")
            cb.set_active(str(idx) in self.config.managed_buttons)
            content.add(cb)
            checks[idx] = cb
        dlg.show_all()
        response = dlg.run()
        checked = ([idx for idx, cb in checks.items() if cb.get_active()]
                  if response == Gtk.ResponseType.OK else None)
        dlg.destroy()
        if checked is None:
            return

        # Base collision-avoidance on the mouse's ACTUAL live signals, not
        # just what we happen to be tracking: a previously-managed button
        # that got unchecked has its fcode dropped from managed_buttons,
        # but the signal stays wired into the mouse's onboard profile (we
        # don't reset it here) — so it must still count as reserved, or a
        # later run could reissue it to a different button.
        reserved = (set(self.config.managed_buttons.values())
                    | ratbag.signals_in_use(buttons))

        try:
            final_managed, new_assignments = ratbag.plan_signal_assignment(
                self.config.managed_buttons, checked, reserved)
        except ratbag.RatbagError as e:
            self._error(f"mouse setup failed: {e}")
            return

        try:
            for idx, fcode in new_assignments.items():
                ratbag.assign_signal(dev, 0, idx, fcode)
            ratbag.set_active_profile(dev, 0)
        except ratbag.RatbagError as e:
            self._error(f"mouse setup failed: {e}")
            return

        self.config.managed_buttons = final_managed
        try:
            C.save(self.config, self.cfg_path)
        except OSError as e:
            self._error(f"mouse configured, but saving config failed: {e}")
            return

        self._prompt_restart_daemon()

    def _prompt_restart_daemon(self):
        dlg = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            text="Mouse set up. The daemon must be restarted to pick up the change.")
        dlg.format_secondary_text(
            "Note: unchecking a button here stops LibreHub from managing "
            "it, but does not restore its original function — it will "
            "keep sending its assigned signal (harmless if unbound) until "
            "you reset it yourself in Piper or ratbagctl.")
        dlg.add_buttons("Restart daemon", Gtk.ResponseType.OK,
                        "I'll restart it myself", Gtk.ResponseType.CANCEL)
        response = dlg.run()
        dlg.destroy()
        if response == Gtk.ResponseType.OK:
            self._restart_daemon()

    def _restart_daemon(self):
        try:
            result = subprocess.run(
                ["systemctl", "--user", "restart", "librehub-daemon"],
                capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError) as e:
            self._error(f"could not restart daemon: {e}")
            return
        if result.returncode == 0:
            self._refresh_status()
            info = Gtk.MessageDialog(
                transient_for=self, modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK, text="Daemon restarted.")
            info.run()
            info.destroy()
        else:
            detail = result.stderr.strip() or f"exit code {result.returncode}"
            self._error(f"daemon restart failed: {detail}")

    def _error(self, text: str, parent=None):
        self._message(text, ok=False, parent=parent)

    def _message(self, text: str, ok: bool = True, parent=None):
        dlg = Gtk.MessageDialog(
            transient_for=parent or self, modal=True,
            message_type=Gtk.MessageType.INFO if ok else Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK, text=text)
        dlg.run()
        dlg.destroy()

    # --- first-run / health-check dialog ---
    def _open_setup_dialog(self, checks=None):
        dlg = Gtk.Dialog(title="LibreHub setup / health check",
                         transient_for=self, modal=True)
        dlg.set_default_size(600, 440)
        content = dlg.get_content_area()
        content.set_spacing(10)
        content.set_border_width(12)

        heading = Gtk.Label()
        heading.set_markup("<b>System check</b>  —  everything LibreHub needs "
                           "to remap your mouse")
        heading.set_xalign(0)
        heading.set_line_wrap(True)
        content.add(heading)

        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.add(list_box)

        summary = Gtk.Label()
        summary.set_xalign(0)
        summary.set_line_wrap(True)
        content.add(summary)

        btn_setup = Gtk.Button(label="Run system setup (asks for password)")
        btn_daemon = Gtk.Button(label="Start daemon")
        btn_restart = Gtk.Button(label="Restart daemon")
        btn_mouse = Gtk.Button(label="Set up mouse")
        btn_recheck = Gtk.Button(label="Re-check")
        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for b in (btn_setup, btn_daemon, btn_restart, btn_mouse):
            action_row.pack_start(b, False, False, 0)
        action_row.pack_end(btn_recheck, False, False, 0)
        content.add(action_row)
        dlg.add_button("Close", Gtk.ResponseType.CLOSE)

        action_btns = (btn_setup, btn_daemon, btn_restart, btn_mouse,
                       btn_recheck)
        # Guards against a worker thread's completion callback touching the
        # dialog after the user has closed it.
        state = {"alive": True}
        dlg.connect("destroy", lambda *_a: state.__setitem__("alive", False))

        def render(checks):
            for child in list_box.get_children():
                list_box.remove(child)
            needs = {c.fix for c in checks if not c.ok}
            for c in checks:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                icon = Gtk.Label(label=_STATUS_ICON[c.status])
                icon.set_valign(Gtk.Align.START)
                row.pack_start(icon, False, False, 0)
                lbl = Gtk.Label()
                lbl.set_xalign(0)
                lbl.set_line_wrap(True)
                text = (f"<b>{GLib.markup_escape_text(c.title)}</b> — "
                        f"{GLib.markup_escape_text(c.detail)}")
                if not c.ok and c.remedy:
                    text += (f"\n<small>{GLib.markup_escape_text(c.remedy)}"
                             "</small>")
                lbl.set_markup(text)
                row.pack_start(lbl, True, True, 0)
                list_box.pack_start(row, False, False, 0)
            btn_setup.set_visible(preflight.FIX_PRIVILEGED in needs)
            btn_daemon.set_visible(preflight.FIX_START_DAEMON in needs)
            btn_restart.set_visible(preflight.FIX_RESTART_DAEMON in needs)
            btn_mouse.set_visible(preflight.FIX_SETUP_MOUSE in needs)
            if all(c.ok for c in checks):
                summary.set_markup("<b>All good — LibreHub is ready.</b>")
            elif preflight.FIX_RELOGIN in needs:
                summary.set_markup(
                    "<b>Almost there:</b> log out and back in (or reboot) to "
                    "activate your new group membership, then click Re-check.")
            else:
                summary.set_text("")
            list_box.show_all()

        def recheck():
            render(preflight.run_all(self.config.managed_buttons))

        def set_busy(msg):
            for b in action_btns:
                b.set_sensitive(False)
            summary.set_markup(f"<i>{GLib.markup_escape_text(msg)}</i>")

        def clear_busy():
            for b in action_btns:
                b.set_sensitive(True)

        def run_async(fn, busy_msg, on_done):
            set_busy(busy_msg)

            def work():
                ok, msg = fn()
                GLib.idle_add(finish, ok, msg)

            def finish(ok, msg):
                if not state["alive"]:  # dialog closed mid-run; don't touch it
                    return False
                clear_busy()
                on_done(ok, msg)
                return False

            threading.Thread(target=work, daemon=True).start()

        def on_setup(_b):
            def done(ok, msg):
                recheck()
                self._message(msg, ok=ok, parent=dlg)
            run_async(preflight.run_privileged_setup,
                      "Running system setup — approve the password prompt…",
                      done)

        def on_daemon(_b):
            def done(ok, msg):
                self._refresh_status()
                recheck()
                if not ok:
                    self._error(msg, parent=dlg)
            run_async(preflight.start_daemon, "Starting daemon…", done)

        def on_restart(_b):
            def done(ok, msg):
                self._refresh_status()
                recheck()
                if not ok:
                    self._error(msg, parent=dlg)
            run_async(preflight.restart_daemon, "Restarting daemon…", done)

        def on_mouse(_b):
            dlg.hide()  # its own dialogs are transient to the main window
            self._on_setup_mouse(None)
            dlg.show()
            self._refresh_status()
            recheck()

        btn_setup.connect("clicked", on_setup)
        btn_daemon.connect("clicked", on_daemon)
        btn_restart.connect("clicked", on_restart)
        btn_mouse.connect("clicked", on_mouse)
        btn_recheck.connect("clicked", lambda _b: recheck())

        initial = (checks if checks is not None
                   else preflight.run_all(self.config.managed_buttons))
        dlg.show_all()
        render(initial)  # after show_all so per-button visibility sticks
        dlg.run()
        dlg.destroy()


def main(argv=None) -> int:
    win = Window()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    win.present()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
