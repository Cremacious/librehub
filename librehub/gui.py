"""GTK3 editor for LibreHub per-game mouse bindings."""
from __future__ import annotations

import os
import socket
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from . import config as C  # noqa: E402
from . import ipc, keys  # noqa: E402


def _ipc_request(msg: dict) -> dict | None:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(11)
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
        self.cfg_path = C.config_path()
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

        # left: game list + add
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
        outer.pack_start(left, False, False, 0)

        # right: bindings table
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.bind_store = Gtk.ListStore(str, str)  # fcode, output key
        self.bind_view = Gtk.TreeView(model=self.bind_store)
        self.bind_view.append_column(
            Gtk.TreeViewColumn("Button (signal)", Gtk.CellRendererText(), text=0))
        key_renderer = Gtk.CellRendererText()
        key_renderer.set_property("editable", True)
        key_renderer.connect("edited", self._on_key_edited)
        self.bind_view.append_column(
            Gtk.TreeViewColumn("Key", key_renderer, text=1))
        right.pack_start(self.bind_view, True, True, 0)
        detect_btn = Gtk.Button(label="Add binding (press a mouse button)")
        detect_btn.connect("clicked", self._on_detect_binding)
        right.pack_start(detect_btn, False, False, 0)
        save_btn = Gtk.Button(label="Save")
        save_btn.connect("clicked", self._on_save)
        right.pack_start(save_btn, False, False, 0)
        self.status = Gtk.Label(label="")
        right.pack_start(self.status, False, False, 0)
        outer.pack_start(right, True, True, 0)

        self._refresh_games()
        self._refresh_status()
        if self._config_warning:
            self.status.set_text(
                f"config error, backed up to .bak — {self.status.get_text()}")
            # defer the modal dialog until the window is actually shown
            self.connect("show", lambda *_a: self._error(self._config_warning))

    # --- helpers ---
    def _refresh_games(self):
        self.game_store.clear()
        self.game_store.append(["", "(default)"])
        for aid, g in self.config.games.items():
            self.game_store.append([aid, f"{g.name} [{aid}]"])

    def _refresh_status(self):
        st = _ipc_request({"cmd": "status"})
        if st and st.get("daemon"):
            self.status.set_text(
                f"daemon: running · device: {st.get('device')} · "
                f"active: {st.get('active_appid') or 'default'}")
        else:
            self.status.set_text("daemon: not running")

    def _selected_game(self) -> C.Game | None:
        model, it = self.game_view.get_selection().get_selected()
        if it is None:
            return None
        aid = model[it][0]
        self._editing = aid or None
        return self.config.default if not aid else self.config.games.get(aid)

    def _flush_bindings(self) -> bool:
        """Write the current bind_store rows into the in-memory game object
        being edited (self._editing, or the default game if None).

        Validates every non-empty output key. If any is invalid, shows an
        error and returns False without touching the model (so the caller
        can abort whatever it was about to do). Returns True otherwise.
        """
        target = (self.config.default if not self._editing
                   else self.config.games.get(self._editing))
        if target is None:
            return True
        bad = []
        bindings: dict[str, str] = {}
        for row in self.bind_store:
            fcode, out = row[0], row[1]
            if not out:
                continue
            try:
                keys.to_code(out)
            except ValueError:
                bad.append(out)
                continue
            bindings[fcode] = out
        if bad:
            self._error(f"invalid key(s): {', '.join(bad)}")
            return False
        target.bindings = bindings
        return True

    def _on_game_selected(self, _sel):
        self._flush_bindings()
        g = self._selected_game()
        self.bind_store.clear()
        if g:
            for fcode, out in g.bindings.items():
                self.bind_store.append([fcode, out])

    def _on_key_edited(self, _renderer, path, new_text):
        text = new_text.strip()
        if text:
            try:
                keys.to_code(text)
            except ValueError:
                self._error(f"invalid key: {text!r}")
                return
        self.bind_store[path][1] = text

    def _on_detect_binding(self, _btn):
        resp = _ipc_request({"cmd": "detect"})
        fcode = (resp or {}).get("fcode")
        if fcode:
            self.bind_store.append([fcode, ""])
        else:
            self._error("No button detected (is the daemon running?).")

    def _on_add_current(self, _btn):
        if not self._flush_bindings():
            return
        resp = _ipc_request({"cmd": "current_appid"})
        aid = (resp or {}).get("appid")
        if not aid:
            self._error("No Steam game focused right now.")
            return
        self.config.games.setdefault(aid, C.Game(name=f"Game {aid}", bindings={}))
        self._refresh_games()

    def _on_add_manual(self, _btn):
        if not self._flush_bindings():
            return
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
                self.config.games.setdefault(aid, C.Game(name=f"Game {aid}", bindings={}))
                self._refresh_games()
        dlg.destroy()

    def _on_save(self, _btn):
        if not self._flush_bindings():
            return
        try:
            C.save(self.config, self.cfg_path)
            self.status.set_text("saved.")
        except OSError as e:
            self._error(f"save failed: {e}")

    def _error(self, text: str):
        dlg = Gtk.MessageDialog(transient_for=self, modal=True,
                                message_type=Gtk.MessageType.ERROR,
                                buttons=Gtk.ButtonsType.OK, text=text)
        dlg.run()
        dlg.destroy()


def main(argv=None) -> int:
    win = Window()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
