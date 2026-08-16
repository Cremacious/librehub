from __future__ import annotations

import re
import socket
import subprocess
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from . import __version__
from . import config as C
from . import focus, ipc, keys, prefs as P, ratbag, theme

_PRIMARY_BUTTON_ACTIONS = {"'button 1'", "'button 2'", "'button 3'"}

_MANIFEST_NAME_RE = re.compile(r'"name"\s+"([^"]*)"')
_LIBRARY_PATH_RE = re.compile(r'"path"\s+"([^"]+)"')

_RESP_BACK = 1
_RESP_SAVE = 2

_GDK_SPECIAL = {
    Gdk.KEY_space: "space", Gdk.KEY_Return: "enter", Gdk.KEY_KP_Enter: "enter",
    Gdk.KEY_Escape: "esc", Gdk.KEY_Tab: "tab", Gdk.KEY_BackSpace: "backspace",
    Gdk.KEY_Delete: "delete", Gdk.KEY_Insert: "insert", Gdk.KEY_Home: "home",
    Gdk.KEY_End: "end", Gdk.KEY_Page_Up: "pageup", Gdk.KEY_Page_Down: "pagedown",
    Gdk.KEY_Up: "up", Gdk.KEY_Down: "down", Gdk.KEY_Left: "left",
    Gdk.KEY_Right: "right", Gdk.KEY_Shift_L: "shift", Gdk.KEY_Shift_R: "shift",
    Gdk.KEY_Control_L: "ctrl", Gdk.KEY_Control_R: "ctrl", Gdk.KEY_Alt_L: "alt",
    Gdk.KEY_Alt_R: "alt", Gdk.KEY_Caps_Lock: "capslock",
}

_PRETTY = {
    "space": "Spacebar", "esc": "Esc", "enter": "Enter", "tab": "Tab",
    "backspace": "Backspace", "delete": "Delete", "insert": "Insert",
    "home": "Home", "end": "End", "pageup": "Page Up", "pagedown": "Page Down",
    "capslock": "Caps Lock", "shift": "Shift", "ctrl": "Ctrl", "alt": "Alt",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
}


def key_name_from_keyval(keyval: int) -> str | None:
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
    if name in _PRETTY:
        return _PRETTY[name]
    if re.fullmatch(r"f\d{1,2}", name):
        return name.upper()
    return name.upper() if len(name) == 1 else name.capitalize()


def button_label(fcode: str, managed_buttons: dict[str, str]) -> str:
    for idx, code in managed_buttons.items():
        if code == fcode:
            return f"Button {idx}"
    return fcode.removeprefix("KEY_")


def parse_library_paths(vdf_text: str) -> list[str]:
    return _LIBRARY_PATH_RE.findall(vdf_text)


def is_valid_appid(text: str) -> bool:
    return text.strip().isdigit()


def _steam_roots() -> list[Path]:
    home = Path.home()
    flatpak = home / ".var" / "app" / "com.valvesoftware.Steam"
    return [home / ".steam" / "steam", home / ".steam" / "root",
            home / ".steam" / "debian-installation",
            home / ".local" / "share" / "Steam",
            flatpak / "data" / "Steam",
            flatpak / ".local" / "share" / "Steam"]


def _steamapps_dirs() -> list[Path]:
    dirs: list[Path] = []
    seen: set[Path] = set()

    def add(sa: Path):
        try:
            key = sa.resolve()
        except OSError:
            key = sa
        if key not in seen:
            seen.add(key)
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
    for path in _steam_manifest_paths(appid):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        m = _MANIFEST_NAME_RE.search(text)
        if m:
            return m.group(1)
    return f"Game {appid}"


def _initial_game_name(games: dict, aid: str) -> str:
    game = games.get(aid)
    if game is not None and game.name:
        return game.name
    return _resolve_game_name(aid)


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


def _avatar(letter: str) -> Gtk.Label:
    a = Gtk.Label(label=letter[:1].upper() if letter else "?")
    a.get_style_context().add_class("avatar")
    a.set_size_request(22, 22)
    return a


def _icon_button(icon_name: str, css: str = "lh-icon") -> Gtk.Button:
    b = Gtk.Button()
    b.add(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU))
    b.get_style_context().add_class(css)
    return b


class ProfileRow(Gtk.ListBoxRow):

    def __init__(self, win, pid: str, name: str, is_default: bool):
        super().__init__()
        self.win = win
        self.pid = pid
        self.is_default = is_default
        self.name = name
        self._editing = False

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(9)
        box.set_margin_bottom(9)
        box.set_margin_start(10)
        box.set_margin_end(10)
        self.add(box)

        self.avatar = _avatar("★" if is_default else name)
        if is_default:
            self.avatar.set_label("★")
        box.pack_start(self.avatar, False, False, 0)

        namecol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self.name_lbl = Gtk.Label(label=name, xalign=0)
        namecol.pack_start(self.name_lbl, False, False, 0)
        if not is_default:
            self.appid_lbl = Gtk.Label(label=pid, xalign=0)
            self.appid_lbl.get_style_context().add_class("appid")
            namecol.pack_start(self.appid_lbl, False, False, 0)
        self.namecol = namecol
        box.pack_start(namecol, True, True, 0)

        self.overflow = None
        if not is_default:
            self.overflow = _icon_button("view-more-symbolic", "lh-overflow")
            self.overflow.set_size_request(22, 22)
            self.overflow.connect("clicked",
                                  lambda _b: self.win.open_row_menu(self))
            box.pack_end(self.overflow, False, False, 0)

        self.connect("button-press-event", self._on_button_press)

    def _on_button_press(self, _w, event):
        if event.button == 3:
            self.win.profile_list.select_row(self)
            self.win.open_row_menu(self)
            return True
        return False

    def start_edit(self):
        if self._editing or self.is_default:
            return
        self._editing = True
        self.get_style_context().add_class("editing")
        self.avatar.get_style_context().add_class("editing")
        self.name_lbl.hide()
        self.entry = Gtk.Entry()
        self.entry.set_text(self.name)
        self.entry.select_region(0, -1)
        self.namecol.pack_start(self.entry, False, False, 0)
        self.namecol.reorder_child(self.entry, 0)
        self.entry.show()
        self.entry.grab_focus()
        self.entry.connect("activate", lambda _e: self._commit())
        self.entry.connect("focus-out-event", lambda *_a: self._commit())
        self.entry.connect("key-press-event", self._on_edit_key)

    def _on_edit_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self._cancel()
            return True
        return False

    def _finish_edit(self):
        self._editing = False
        self.get_style_context().remove_class("editing")
        self.avatar.get_style_context().remove_class("editing")
        if getattr(self, "entry", None) is not None:
            self.entry.destroy()
            self.entry = None
        self.name_lbl.show()

    def _cancel(self):
        self._finish_edit()

    def _commit(self):
        if not self._editing:
            return
        new = self.entry.get_text().strip()
        self._finish_edit()
        if new and new != self.name:
            self.win.commit_rename(self.pid, new)


class BindingRow(Gtk.ListBoxRow):
    def __init__(self, win, fcode: str, keyname: str):
        super().__init__()
        self.win = win
        self.fcode = fcode
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(8)
        box.set_margin_end(8)
        self.add(box)

        chip = Gtk.Label(label=button_label(fcode, win.config.managed_buttons))
        chip.get_style_context().add_class("chip")
        box.pack_start(chip, False, False, 0)

        arrow = Gtk.Image.new_from_icon_name("go-next-symbolic",
                                             Gtk.IconSize.MENU)
        arrow.get_style_context().add_class("arrow")
        box.pack_start(arrow, False, False, 0)

        cap = Gtk.Label(label=pretty_key(keyname))
        cap.get_style_context().add_class("keycap")
        box.pack_start(cap, False, False, 0)

        code = Gtk.Label(label=fcode, xalign=0)
        code.get_style_context().add_class("keycode")
        box.pack_start(code, True, True, 0)

        rm = _icon_button("window-close-symbolic", "remove")
        rm.connect("clicked", lambda _b: win.remove_binding(fcode))
        box.pack_end(rm, False, False, 0)


class MainWindow(Gtk.Window):
    def __init__(self, prefs: P.Prefs | None = None):
        super().__init__(title="LibreHub")
        self.prefs = prefs or P.load()
        self.get_style_context().add_class("lh-root")
        theme.apply_appearance(self.prefs.appearance)
        self.set_default_size(900, 600)
        self.set_size_request(900, 600)
        self.set_keep_above(self.prefs.keep_above)

        self.cfg_path = C.config_path()
        try:
            self.config = C.load(self.cfg_path)
        except C.ConfigError:
            self.config = C.default_config()
        self._selected_pid: str | None = None
        self._banner_kind: str | None = None

        self._build_header()
        self._build_body()

        self._refresh_profiles()
        self._refresh_status()
        GLib.timeout_add_seconds(2, self._poll_status)

    def _build_header(self):
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.get_style_context().add_class("lh-header")
        hb.set_custom_title(Gtk.Box())

        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label(label="LibreHub")
        lbl.get_style_context().add_class("lh-title")
        title_box.pack_start(lbl, False, False, 0)

        self.pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.pill.get_style_context().add_class("status-pill")
        self.pill.set_valign(Gtk.Align.CENTER)
        dot = Gtk.Box()
        dot.get_style_context().add_class("status-dot")
        dot.set_valign(Gtk.Align.CENTER)
        self.pill.pack_start(dot, False, False, 0)
        self.pill_lbl = Gtk.Label(label="Remapping active")
        self.pill.pack_start(self.pill_lbl, False, False, 0)
        title_box.pack_start(self.pill, False, False, 0)
        hb.pack_start(title_box)

        menu_btn = Gtk.MenuButton()
        menu_btn.add(Gtk.Image.new_from_icon_name("open-menu-symbolic",
                                                  Gtk.IconSize.MENU))
        menu_btn.get_style_context().add_class("lh-icon")
        menu_btn.set_popover(self._build_app_menu())
        hb.pack_end(menu_btn)

        self.set_titlebar(hb)

    def _build_app_menu(self) -> Gtk.Popover:
        pop = Gtk.Popover()
        pop.get_style_context().add_class("lh-popover")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for label, cb in (
            ("Preferences", self._show_preferences),
            ("Set up mouse", lambda: show_setup_mouse(self, self)),
            ("Run health check", self._show_health_check),
            ("About", self._show_about),
        ):
            b = Gtk.Button(label=label)
            b.set_relief(Gtk.ReliefStyle.NONE)
            b.get_style_context().add_class("popover-item")
            b.connect("clicked", lambda _b, f=cb: (pop.popdown(), f()))
            box.pack_start(b, False, False, 0)
        box.show_all()
        pop.add(box)
        return pop

    def _build_body(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(outer)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar.get_style_context().add_class("lh-sidebar")
        sidebar.set_size_request(250, -1)
        header = Gtk.Label(label="PROFILES", xalign=0)
        header.get_style_context().add_class("section-header")
        sidebar.pack_start(header, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.profile_list = Gtk.ListBox()
        self.profile_list.get_style_context().add_class("profile-list")
        self.profile_list.connect("row-selected", self._on_profile_selected)
        self.profile_list.connect("key-press-event", self._on_list_key)
        scroller.add(self.profile_list)
        sidebar.pack_start(scroller, True, True, 0)

        footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        footer.get_style_context().add_class("sidebar-footer")
        add_btn = Gtk.Button(label="+ Add game")
        add_btn.get_style_context().add_class("lh-secondary")
        add_btn.get_style_context().add_class("add-game")
        add_btn.connect("clicked", lambda _b: self._show_add_game())
        footer.pack_start(add_btn, False, False, 0)
        sidebar.pack_start(footer, False, False, 0)
        outer.pack_start(sidebar, False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.get_style_context().add_class("lh-root")
        outer.pack_start(content, True, True, 0)

        titleblock = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        titleblock.get_style_context().add_class("title-block")
        titlecol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.title_lbl = Gtk.Label(label="", xalign=0)
        self.title_lbl.get_style_context().add_class("game-title")
        self.subtitle_lbl = Gtk.Label(label="", xalign=0)
        self.subtitle_lbl.get_style_context().add_class("subtitle")
        self.subtitle_lbl.set_line_wrap(True)
        titlecol.pack_start(self.title_lbl, False, False, 0)
        titlecol.pack_start(self.subtitle_lbl, False, False, 0)
        titleblock.pack_start(titlecol, True, True, 0)
        self.add_binding_btn = Gtk.Button(label="Add binding")
        self.add_binding_btn.get_style_context().add_class("lh-primary")
        self.add_binding_btn.connect("clicked",
                                     lambda _b: self._add_binding_flow())
        titleblock.pack_end(self.add_binding_btn, False, False, 0)
        content.pack_start(titleblock, False, False, 0)

        self.banner = self._build_banner()
        self.banner.set_no_show_all(True)
        content.pack_start(self.banner, False, False, 0)

        self.body_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.pack_start(self.body_area, True, True, 0)

        self.bind_scroller = Gtk.ScrolledWindow()
        self.bind_scroller.set_policy(Gtk.PolicyType.NEVER,
                                      Gtk.PolicyType.AUTOMATIC)
        self.bind_scroller.set_margin_top(8)
        self.bind_scroller.set_margin_bottom(8)
        self.bind_scroller.set_margin_start(16)
        self.bind_scroller.set_margin_end(16)
        self.bind_list = Gtk.ListBox()
        self.bind_list.get_style_context().add_class("bindings")
        self.bind_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.bind_scroller.add(self.bind_list)
        self.body_area.pack_start(self.bind_scroller, True, True, 0)

        self.empty_state = self._build_empty_state()
        self.empty_state.set_no_show_all(True)
        self.body_area.pack_start(self.empty_state, True, True, 0)

        self.footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.footer.get_style_context().add_class("footer-bar")
        self.footer_left = Gtk.Label(label="", xalign=0)
        self.footer.pack_start(self.footer_left, True, True, 0)
        saved = Gtk.Label(label="Saved automatically")
        self.footer.pack_end(saved, False, False, 0)
        content.pack_start(self.footer, False, False, 0)

    def _build_banner(self) -> Gtk.Box:
        b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
        b.get_style_context().add_class("banner")
        b.set_margin_top(16)
        b.set_margin_start(18)
        b.set_margin_end(18)
        glyph = Gtk.Image.new_from_icon_name("dialog-warning-symbolic",
                                             Gtk.IconSize.MENU)
        glyph.get_style_context().add_class("banner-glyph")
        glyph.set_valign(Gtk.Align.START)
        b.pack_start(glyph, False, False, 0)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.banner_title = Gtk.Label(label="Remapping is paused", xalign=0)
        self.banner_title.get_style_context().add_class("banner-title")
        self.banner_body = Gtk.Label(xalign=0, label="")
        self.banner_body.get_style_context().add_class("banner-body")
        self.banner_body.set_line_wrap(True)
        col.pack_start(self.banner_title, False, False, 0)
        col.pack_start(self.banner_body, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        restart = Gtk.Button(label="Restart daemon")
        restart.get_style_context().add_class("lh-primary")
        restart.connect("clicked", lambda _b: self._restart_daemon())
        row.pack_start(restart, False, False, 0)
        col.pack_start(row, False, False, 0)
        b.pack_start(col, True, True, 0)
        return b

    def _build_empty_state(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        t = Gtk.Label(label="No bindings for this game")
        t.get_style_context().add_class("empty-title")
        body = Gtk.Label(label="Press Add binding, click a mouse button, then "
                               "the key it should send.")
        body.get_style_context().add_class("empty-body")
        body.set_line_wrap(True)
        body.set_justify(Gtk.Justification.CENTER)
        body.set_max_width_chars(36)
        btn = Gtk.Button(label="Add binding")
        btn.get_style_context().add_class("lh-primary")
        btn.set_halign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda _b: self._add_binding_flow())
        box.pack_start(t, False, False, 0)
        box.pack_start(body, False, False, 0)
        box.pack_start(btn, False, False, 0)
        return box

    def _profiles(self):
        items = [("default", "Default", self.config.default, True)]
        for aid, g in self.config.games.items():
            items.append((aid, g.name, g, False))
        return items

    def _refresh_profiles(self):
        prev = self._selected_pid
        for child in self.profile_list.get_children():
            self.profile_list.remove(child)
        want_row = None
        for pid, name, _game, is_default in self._profiles():
            row = ProfileRow(self, pid, name, is_default)
            self.profile_list.add(row)
            if pid == prev:
                want_row = row
        self.profile_list.show_all()
        if want_row is None:
            want_row = self.profile_list.get_row_at_index(0)
        if want_row is not None:
            self.profile_list.select_row(want_row)

    def _on_profile_selected(self, _list, row):
        if row is None:
            return
        self._selected_pid = row.pid
        self._refresh_content()

    def _selected_game(self) -> C.Game | None:
        if self._selected_pid is None:
            return None
        if self._selected_pid == "default":
            return self.config.default
        return self.config.games.get(self._selected_pid)

    def _refresh_content(self):
        game = self._selected_game()
        if game is None:
            return
        is_default = self._selected_pid == "default"
        self.title_lbl.set_text("Default profile" if is_default else game.name)
        n = len(game.bindings)
        plural = "" if n == 1 else "s"
        if is_default:
            self.subtitle_lbl.set_text(
                f"{n} button{plural} bound · used when no mapped game is focused")
        else:
            self.subtitle_lbl.set_text(
                f"{n} button{plural} bound · switches on automatically when "
                "this game is focused")
        for child in self.bind_list.get_children():
            self.bind_list.remove(child)
        for fcode, keyname in game.bindings.items():
            self.bind_list.add(BindingRow(self, fcode, keyname))
        self.bind_list.show_all()
        has = n > 0
        self.bind_scroller.set_visible(has)
        self.empty_state.set_visible(not has)

    def _poll_status(self) -> bool:
        self._refresh_status()
        return True

    def _refresh_status(self):
        st = _ipc_request({"cmd": "status"}, timeout=1.5)
        ctx = self.pill.get_style_context()
        session = "X11 · per-window switching"
        device = "no mouse"
        if st and st.get("daemon"):
            device = st.get("device") or device
            if st.get("remapping"):
                ctx.remove_class("paused")
                self.pill_lbl.set_text("Remapping active")
                self._set_banner(None)
            else:
                ctx.add_class("paused")
                self.pill_lbl.set_text("Remapping paused")
                self._set_banner(
                    "paused", "Remapping is paused",
                    "The daemon can't reach your mouse. Restarting it usually "
                    "fixes this.")
        else:
            ctx.add_class("paused")
            self.pill_lbl.set_text("Daemon stopped")
            self._set_banner(
                "stopped", "Daemon not running",
                "Start it from the app menu → Run health check.")
        self.footer_left.set_markup(
            f"{GLib.markup_escape_text(device)}  ·  {session}")

    def _set_banner(self, kind, title="", body=""):
        if kind == self._banner_kind:
            return
        self._banner_kind = kind
        if kind is None:
            self.banner.hide()
            return
        self.banner_title.set_text(title)
        self.banner_body.set_text(body)
        self.banner.show()
        self.banner.show_all()

    def _on_list_key(self, _w, event):
        row = self.profile_list.get_selected_row()
        if not isinstance(row, ProfileRow):
            return False
        if event.keyval == Gdk.KEY_F2:
            row.start_edit()
            return True
        if event.keyval == Gdk.KEY_Delete and not row.is_default:
            self._remove_game(row.pid)
            return True
        return False

    def open_row_menu(self, row: ProfileRow):
        pop = Gtk.Popover()
        pop.get_style_context().add_class("lh-popover")
        pop.set_relative_to(row.overflow if row.overflow is not None else row)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        def item(label, cb, destructive=False):
            b = Gtk.Button(label=label)
            b.set_relief(Gtk.ReliefStyle.NONE)
            b.get_style_context().add_class("popover-item")
            if destructive:
                b.get_style_context().add_class("destructive")
            b.connect("clicked", lambda _b: (pop.popdown(), cb()))
            box.pack_start(b, False, False, 0)

        if not row.is_default:
            item("Rename…", row.start_edit)
            item("Duplicate bindings to…", lambda: self._duplicate_to(row.pid))
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            sep.set_margin_top(4)
            sep.set_margin_bottom(4)
            box.pack_start(sep, False, False, 0)
            item("Remove game", lambda: self._remove_game(row.pid),
                 destructive=True)
        else:
            item("Duplicate bindings to…", lambda: self._duplicate_to("default"))
        box.show_all()
        pop.add(box)
        pop.popup()

    def commit_rename(self, pid: str, new_name: str):
        game = self.config.games.get(pid)
        if game is None or new_name == game.name:
            return
        game.name = new_name
        if self._persist():
            self._refresh_profiles()
            self._confirm(f"Renamed to “{new_name}”")

    def _duplicate_to(self, src_pid: str):
        src = (self.config.default if src_pid == "default"
               else self.config.games.get(src_pid))
        if src is None or not src.bindings:
            self._error("That profile has no bindings to copy.")
            return
        targets = [("default", "Default")] + [
            (aid, g.name) for aid, g in self.config.games.items()
            if aid != src_pid]
        if not targets:
            self._error("No other profile to copy to. Add a game first.")
            return
        dlg = self._dialog("Duplicate bindings", width=480)
        c = dlg.get_content_area()
        c.set_border_width(16)
        c.add(Gtk.Label(label="Copy these bindings to:", xalign=0))
        combo = Gtk.ComboBoxText()
        for aid, name in targets:
            combo.append(aid, name)
        combo.set_active(0)
        c.add(combo)
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        ok = dlg.add_button("Copy", Gtk.ResponseType.OK)
        ok.get_style_context().add_class("lh-primary")
        dlg.show_all()
        resp = dlg.run()
        target = combo.get_active_id()
        dlg.destroy()
        if resp != Gtk.ResponseType.OK or not target:
            return
        dst = (self.config.default if target == "default"
               else self.config.games.get(target))
        dst.bindings.update(dict(src.bindings))
        if self._persist():
            self._refresh_profiles()
            self._refresh_content()
            self._confirm("Bindings copied.")

    def _remove_game(self, pid: str):
        game = self.config.games.get(pid)
        if game is None:
            return
        confirm = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"Remove '{game.name}' [{pid}]?")
        confirm.format_secondary_text(
            "This deletes its bindings from LibreHub. (It does not change the "
            "mouse's onboard button signals.)")
        resp = confirm.run()
        confirm.destroy()
        if resp != Gtk.ResponseType.OK:
            return
        self.config.games.pop(pid, None)
        self._selected_pid = "default"
        if self._persist():
            self._refresh_profiles()

    def _show_add_game(self):
        dlg = self._dialog("Add game", right="1 of 2", width=480)
        c = dlg.get_content_area()
        c.set_border_width(0)
        state: dict = {"aid": None, "entry": None}

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        c.add(body)
        slot = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        body.pack_start(slot, True, True, 0)
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer.get_style_context().add_class("action-bar")
        body.pack_end(footer, False, False, 0)

        def _btn(label, primary=False):
            b = Gtk.Button(label=label)
            b.get_style_context().add_class("lh-primary" if primary
                                            else "lh-secondary")
            return b

        close = _btn("Close")
        close.connect("clicked",
                      lambda _b: dlg.response(Gtk.ResponseType.CLOSE))
        back = _btn("Back")
        back.connect("clicked", lambda _b: dlg.response(_RESP_BACK))
        save = _btn("Save", primary=True)
        save.connect("clicked", lambda _b: dlg.response(_RESP_SAVE))
        footer.pack_start(back, False, False, 0)
        footer.pack_end(save, False, False, 0)
        footer.pack_end(close, False, False, 0)

        def swap(child):
            for ch in slot.get_children():
                slot.remove(ch)
            slot.add(child)

        def go_step1():
            state["aid"] = None
            state["entry"] = None
            dlg.get_titlebar().set_custom_title(
                _dialog_title("Add game", "1 of 2"))
            swap(self._add_game_picker(go_step2))
            dlg.show_all()
            back.hide()
            save.hide()

        def go_step2(aid):
            state["aid"] = aid
            dlg.get_titlebar().set_custom_title(
                _dialog_title("Add game", "2 of 2"))
            widget, entry = self._add_game_namer(aid)
            state["entry"] = entry
            swap(widget)
            dlg.show_all()
            close.hide()
            entry.grab_focus()
            entry.connect("activate", lambda _e: dlg.response(_RESP_SAVE))

        go_step1()
        while True:
            resp = dlg.run()
            if resp != _RESP_BACK:
                break
            go_step1()

        aid = state["aid"]
        name = state["entry"].get_text().strip() if state["entry"] else ""
        dlg.destroy()
        if resp == _RESP_SAVE and aid:
            self._add_game(aid,
                           name or _initial_game_name(self.config.games, aid))

    def _add_game_picker(self, on_pick):
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        wrap.set_margin_top(18)
        wrap.set_margin_start(22)
        wrap.set_margin_end(22)

        wrap.add(Gtk.Label(label="Running now", xalign=0))
        running = [a for a in focus.running_appids()
                   if a not in self.config.games]
        card = Gtk.ListBox()
        card.get_style_context().add_class("card")
        card.set_selection_mode(Gtk.SelectionMode.NONE)
        if running:
            for i, aid in enumerate(running):
                card.add(self._detected_row(aid, primary=(i == 0),
                                            on_pick=on_pick))
        else:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label="No running Steam game detected.", xalign=0)
            lbl.get_style_context().add_class("subtitle")
            lbl.set_margin_top(11)
            lbl.set_margin_bottom(11)
            lbl.set_margin_start(13)
            row.add(lbl)
            card.add(row)
        wrap.add(card)

        sep = Gtk.Label(label="Not listed? Enter an AppID", xalign=0)
        sep.set_margin_top(6)
        wrap.add(sep)

        manual = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        entry = Gtk.Entry()
        entry.get_style_context().add_class("lh-entry")
        entry.set_placeholder_text("Steam AppID (e.g. 1086940)")
        entry.set_hexpand(True)
        manual.pack_start(entry, True, True, 0)
        add = Gtk.Button(label="Next")
        add.get_style_context().add_class("lh-secondary")
        add.set_sensitive(False)

        def add_manual(*_a):
            if is_valid_appid(entry.get_text()):
                on_pick(entry.get_text().strip())
        add.connect("clicked", add_manual)
        entry.connect("activate", add_manual)
        entry.connect("changed", lambda e: add.set_sensitive(
            is_valid_appid(e.get_text())))
        manual.pack_start(add, False, False, 0)
        wrap.add(manual)
        return wrap

    def _add_game_namer(self, aid: str):
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        wrap.set_margin_top(22)
        wrap.set_margin_bottom(16)
        wrap.set_margin_start(22)
        wrap.set_margin_end(22)

        resolved = _initial_game_name(self.config.games, aid)
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        head.pack_start(_avatar(resolved), False, False, 0)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hl = Gtk.Label(label="Name this game", xalign=0)
        hl.get_style_context().add_class("dialog-headline")
        col.pack_start(hl, False, False, 0)
        ap = Gtk.Label(label=f"AppID {aid}", xalign=0)
        ap.get_style_context().add_class("keycode")
        col.pack_start(ap, False, False, 0)
        head.pack_start(col, True, True, 0)
        wrap.add(head)

        entry = Gtk.Entry()
        entry.get_style_context().add_class("lh-entry")
        entry.set_text(resolved)
        entry.select_region(0, -1)
        wrap.add(entry)

        hint = Gtk.Label(label="This is the name shown in the sidebar. You "
                               "can rename it later.", xalign=0)
        hint.get_style_context().add_class("dialog-body")
        hint.set_line_wrap(True)
        wrap.add(hint)
        return wrap, entry

    def _detected_row(self, aid, primary, on_pick):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(11)
        box.set_margin_bottom(11)
        box.set_margin_start(13)
        box.set_margin_end(13)
        name = _resolve_game_name(aid)
        box.pack_start(_avatar(name), False, False, 0)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        col.pack_start(Gtk.Label(label=name, xalign=0), False, False, 0)
        ap = Gtk.Label(label=aid, xalign=0)
        ap.get_style_context().add_class("keycode")
        col.pack_start(ap, False, False, 0)
        box.pack_start(col, True, True, 0)
        btn = Gtk.Button(label="Next")
        btn.get_style_context().add_class("lh-primary" if primary
                                          else "lh-secondary")
        btn.connect("clicked", lambda _b: on_pick(aid))
        box.pack_end(btn, False, False, 0)
        row.add(box)
        return row

    def _add_game(self, aid: str, name: str):
        game = self.config.games.get(aid)
        if game is None:
            self.config.games[aid] = C.Game(name=name, bindings={})
        else:
            game.name = name
        self._selected_pid = aid
        if self._persist():
            self._refresh_profiles()

    def _add_binding_flow(self):
        game = self._selected_game()
        if game is None:
            self._error("Select a game or the default profile first.")
            return
        dlg = self._dialog("Add binding", right="1 of 2", width=480)
        c = dlg.get_content_area()
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)

        step = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        step.set_halign(Gtk.Align.CENTER)
        step.set_margin_top(28)
        step.set_margin_bottom(16)
        circle = Gtk.Label(label="◉")
        circle.get_style_context().add_class("wait-circle")
        circle.set_size_request(54, 54)
        spinner = Gtk.Spinner()
        spinner.start()
        headline = Gtk.Label(label="Press a mouse button")
        headline.get_style_context().add_class("dialog-headline")
        body = Gtk.Label(label="Any of the buttons you set up. Waiting…")
        body.get_style_context().add_class("dialog-body")
        body.set_line_wrap(True)
        body.set_justify(Gtk.Justification.CENTER)
        step.pack_start(circle, False, False, 0)
        step.pack_start(spinner, False, False, 0)
        step.pack_start(headline, False, False, 0)
        step.pack_start(body, False, False, 0)
        c.add(step)
        dlg.show_all()

        state = {"alive": True, "fcode": None, "key": None}

        def detect_worker():
            resp = _ipc_request({"cmd": "detect"})
            GLib.idle_add(on_detected, resp)

        def on_detected(resp):
            if not state["alive"]:
                return False
            fcode = (resp or {}).get("fcode")
            if not fcode:
                self._error(
                    "No button detected. Make sure the daemon is running and "
                    "you've set up your mouse, then try again.", parent=dlg)
                dlg.response(Gtk.ResponseType.CANCEL)
                return False
            state["fcode"] = fcode
            spinner.stop()
            go_step2(fcode)
            return False

        def go_step2(fcode):
            dlg.get_titlebar().set_custom_title(_dialog_title("Add binding",
                                                              "2 of 2"))
            for ch in c.get_children():
                c.remove(ch)
            s2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            s2.set_halign(Gtk.Align.CENTER)
            s2.set_margin_top(24)
            s2.set_margin_bottom(16)
            preview = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            preview.set_halign(Gtk.Align.CENTER)
            chip = Gtk.Label(label=button_label(fcode,
                                                self.config.managed_buttons))
            chip.get_style_context().add_class("chip")
            arrow = Gtk.Image.new_from_icon_name("go-next-symbolic",
                                                 Gtk.IconSize.MENU)
            arrow.get_style_context().add_class("arrow")
            slot = Gtk.Label(label="?")
            slot.get_style_context().add_class("pending-slot")
            preview.pack_start(chip, False, False, 0)
            preview.pack_start(arrow, False, False, 0)
            preview.pack_start(slot, False, False, 0)
            hl = Gtk.Label(label="Now press the key it should send")
            hl.get_style_context().add_class("dialog-headline")
            bd = Gtk.Label(label="Letters, numbers, arrows, Space, Enter and "
                                 "F-keys work.")
            bd.get_style_context().add_class("dialog-body")
            bd.set_line_wrap(True)
            bd.set_justify(Gtk.Justification.CENTER)
            s2.pack_start(preview, False, False, 0)
            s2.pack_start(hl, False, False, 0)
            s2.pack_start(bd, False, False, 0)
            c.add(s2)
            c.show_all()

            def on_key(_w, event):
                name = key_name_from_keyval(event.keyval)
                if name is None:
                    bd.set_text("Unsupported key — try a letter, number, "
                                "arrow, Space, Enter or an F-key.")
                    return True
                state["key"] = name
                slot.set_label(pretty_key(name))
                slot.get_style_context().remove_class("pending-slot")
                slot.get_style_context().add_class("keycap")
                dlg.response(Gtk.ResponseType.OK)
                return True
            dlg.connect("key-press-event", on_key)

        threading.Thread(target=detect_worker, daemon=True).start()
        resp = dlg.run()
        state["alive"] = False
        dlg.destroy()
        if resp == Gtk.ResponseType.OK and state["fcode"] and state["key"]:
            game.bindings[state["fcode"]] = state["key"]
            if self._persist():
                self._refresh_content()
                self._refresh_profiles()
                self._confirm(f"Bound to {pretty_key(state['key'])}.")

    def remove_binding(self, fcode: str):
        game = self._selected_game()
        if game is None:
            return
        game.bindings.pop(fcode, None)
        if self._persist():
            self._refresh_content()
            self._refresh_profiles()

    def _show_preferences(self):
        dlg = self._dialog("Preferences", width=480)
        c = dlg.get_content_area()
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        wrap.set_margin_top(16)
        wrap.set_margin_start(20)
        wrap.set_margin_end(20)
        wrap.set_margin_bottom(18)
        c.add(wrap)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.get_style_context().add_class("card")

        def switch_row(label, value, on_toggle):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            row.set_margin_top(12)
            row.set_margin_bottom(12)
            row.set_margin_start(14)
            row.set_margin_end(14)
            row.pack_start(Gtk.Label(label=label, xalign=0), True, True, 0)
            sw = Gtk.Switch()
            sw.set_active(value)
            sw.connect("state-set", lambda _s, v: (on_toggle(v), False)[1])
            sw.set_valign(Gtk.Align.CENTER)
            row.pack_end(sw, False, False, 0)
            card.pack_start(row, False, False, 0)

        switch_row("Keep window above games", self.prefs.keep_above,
                   self._set_keep_above)
        switch_row("Start daemon at login", self.prefs.start_at_login,
                   self._set_start_at_login)
        switch_row("Show tray icon", self.prefs.tray_icon, self._set_tray)
        wrap.add(card)

        wrap.add(Gtk.Label(label="Appearance", xalign=0))
        seg = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        seg.get_style_context().add_class("linked")
        group = None
        for value, text in (("system", "System"), ("light", "Light"),
                            ("dark", "Dark")):
            rb = Gtk.RadioButton.new_with_label_from_widget(group, text)
            rb.set_mode(False)
            group = group or rb
            if self.prefs.appearance == value:
                rb.set_active(True)
            rb.connect("toggled", lambda b, v=value: b.get_active()
                       and self._set_appearance(v))
            seg.pack_start(rb, True, True, 0)
        wrap.add(seg)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        st = _ipc_request({"cmd": "status"}, timeout=1.5)
        dev = (st or {}).get("device") if st else None
        state = ("Daemon running · " + dev) if (st and st.get("daemon") and dev
                                                ) else "Daemon not running"
        bottom.pack_start(Gtk.Label(label=state, xalign=0), True, True, 0)
        hc = Gtk.Button(label="Run health check")
        hc.get_style_context().add_class("lh-secondary")
        hc.connect("clicked", lambda _b: (dlg.destroy(),
                                          self._show_health_check()))
        bottom.pack_end(hc, False, False, 0)
        wrap.add(bottom)

        dlg.add_button("Close", Gtk.ResponseType.CLOSE)
        dlg.show_all()
        dlg.run()
        dlg.destroy()

    def _set_keep_above(self, value):
        self.prefs.keep_above = value
        self.set_keep_above(value)
        P.save(self.prefs)

    def _set_start_at_login(self, value):
        self.prefs.start_at_login = value
        P.save(self.prefs)
        action = "enable" if value else "disable"
        try:
            subprocess.run(["systemctl", "--user", action, "librehub-daemon"],
                           capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass

    def _set_tray(self, value):
        self.prefs.tray_icon = value
        P.save(self.prefs)

    def _set_appearance(self, value):
        self.prefs.appearance = value
        P.save(self.prefs)
        theme.apply_appearance(value)

    def _restart_daemon(self):
        from . import preflight
        ok, msg = preflight.restart_daemon()
        self._refresh_status()
        if not ok:
            self._error(msg)
        else:
            self._confirm("Daemon restarted.")

    def _show_health_check(self):
        show_health_check(self)

    def _show_about(self):
        d = Gtk.AboutDialog(transient_for=self, modal=True)
        d.set_program_name("LibreHub")
        d.set_version(__version__)
        d.set_logo_icon_name(theme.ICON_NAME)
        d.set_comments("Per-game mouse-button remapper for Linux.")
        d.run()
        d.destroy()

    def _persist(self) -> bool:
        try:
            C.save(self.config, self.cfg_path)
            return True
        except OSError as e:
            self._error(f"save failed: {e}")
            return False

    def _confirm(self, text: str):
        self.footer_left.set_text(text)
        GLib.timeout_add_seconds(3, lambda: (self._refresh_status(), False)[1])

    def _dialog(self, title: str, right: str | None = None,
                width: int = 480) -> Gtk.Dialog:
        dlg = Gtk.Dialog(transient_for=self, modal=True)
        dlg.set_resizable(False)
        dlg.set_default_size(width, -1)
        dlg.get_style_context().add_class("lh-root")
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.get_style_context().add_class("lh-header")
        hb.set_custom_title(_dialog_title(title, right))
        dlg.set_titlebar(hb)
        return dlg

    def _error(self, text: str, parent=None):
        dlg = Gtk.MessageDialog(
            transient_for=parent or self, modal=True,
            message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK,
            text=text)
        dlg.run()
        dlg.destroy()


def _dialog_title(title: str, right: str | None) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    lbl = Gtk.Label(label=title)
    lbl.get_style_context().add_class("lh-title")
    box.pack_start(lbl, False, False, 0)
    if right:
        r = Gtk.Label(label=right)
        r.get_style_context().add_class("step-counter")
        box.pack_end(r, False, False, 0)
    box.show_all()
    return box


def show_setup_mouse(parent: Gtk.Window, win: "MainWindow | None" = None):
    config = win.config if win else C.load(C.config_path())
    cfg_path = win.cfg_path if win else C.config_path()

    def err(msg):
        d = Gtk.MessageDialog(transient_for=parent, modal=True,
                              message_type=Gtk.MessageType.ERROR,
                              buttons=Gtk.ButtonsType.OK, text=msg)
        d.run()
        d.destroy()

    try:
        dev = ratbag.resolve_device()
    except ratbag.RatbagError as e:
        return err(f"could not detect mouse: {e}")
    if not dev:
        return err("No supported mouse found.")
    try:
        info = ratbag.device_info(dev)
    except ratbag.RatbagError as e:
        return err(f"could not read mouse info: {e}")
    buttons = ratbag.parse_profile_buttons(info, 0)
    remappable = {i: a for i, a in buttons.items()
                  if a not in _PRIMARY_BUTTON_ACTIONS}
    if not remappable:
        return err("No remappable buttons found on this mouse.")

    dlg = Gtk.Dialog(title="Pick the buttons to manage", transient_for=parent,
                     modal=True)
    dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
    ok = dlg.add_button("Apply", Gtk.ResponseType.OK)
    ok.get_style_context().add_class("lh-primary")
    c = dlg.get_content_area()
    c.set_border_width(14)
    switches = {}
    for idx in sorted(remappable):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.pack_start(Gtk.Label(label=f"Button {idx} — currently "
                                       f"{remappable[idx]}", xalign=0),
                       True, True, 0)
        sw = Gtk.Switch()
        sw.set_active(str(idx) in config.managed_buttons)
        sw.set_valign(Gtk.Align.CENTER)
        row.pack_end(sw, False, False, 0)
        c.add(row)
        switches[idx] = sw
    dlg.show_all()
    resp = dlg.run()
    checked = [i for i, s in switches.items() if s.get_active()
               ] if resp == Gtk.ResponseType.OK else None
    dlg.destroy()
    if checked is None:
        return

    reserved = (set(config.managed_buttons.values())
                | ratbag.signals_in_use(buttons))
    try:
        final, new = ratbag.plan_signal_assignment(
            config.managed_buttons, checked, reserved)
        for idx, fcode in new.items():
            ratbag.assign_signal(dev, 0, idx, fcode)
        ratbag.set_active_profile(dev, 0)
    except ratbag.RatbagError as e:
        return err(f"mouse setup failed: {e}")
    config.managed_buttons = final
    try:
        C.save(config, cfg_path)
    except OSError as e:
        return err(f"mouse configured, but saving config failed: {e}")
    try:
        subprocess.run(["systemctl", "--user", "restart", "librehub-daemon"],
                       capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass
    if win:
        win._refresh_content()


def show_health_check(parent: Gtk.Window):
    from . import preflight
    dlg = Gtk.Dialog(title="Health check", transient_for=parent, modal=True)
    dlg.set_default_size(520, -1)
    c = dlg.get_content_area()
    c.set_border_width(14)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    c.add(box)
    summary = Gtk.Label(xalign=0)
    summary.set_line_wrap(True)
    row_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    b_setup = Gtk.Button(label="Run system setup")
    b_setup.get_style_context().add_class("lh-primary")
    b_daemon = Gtk.Button(label="Start daemon")
    b_daemon.get_style_context().add_class("lh-secondary")
    b_restart = Gtk.Button(label="Restart daemon")
    b_restart.get_style_context().add_class("lh-secondary")
    b_mouse = Gtk.Button(label="Set up mouse")
    b_mouse.get_style_context().add_class("lh-secondary")
    for b in (b_setup, b_daemon, b_restart, b_mouse):
        row_btns.pack_start(b, False, False, 0)

    managed = {}
    try:
        managed = C.load(C.config_path()).managed_buttons
    except C.ConfigError:
        pass

    def render():
        for ch in box.get_children():
            box.remove(ch)
        checks = preflight.run_all(managed)
        needs = {c.fix for c in checks if not c.ok}
        for chk in checks:
            icon = {preflight.Status.OK: "✅", preflight.Status.WARN: "⚠️",
                    preflight.Status.FAIL: "❌"}[chk.status]
            lbl = Gtk.Label(xalign=0)
            lbl.set_line_wrap(True)
            txt = (f"{icon}  <b>{GLib.markup_escape_text(chk.title)}</b> — "
                   f"{GLib.markup_escape_text(chk.detail)}")
            if not chk.ok and chk.remedy:
                txt += (f"\n<small>{GLib.markup_escape_text(chk.remedy)}"
                        "</small>")
            lbl.set_markup(txt)
            box.pack_start(lbl, False, False, 0)
        box.pack_start(summary, False, False, 0)
        box.pack_start(row_btns, False, False, 0)
        b_setup.set_visible(preflight.FIX_PRIVILEGED in needs)
        b_daemon.set_visible(preflight.FIX_START_DAEMON in needs)
        b_restart.set_visible(preflight.FIX_RESTART_DAEMON in needs)
        b_mouse.set_visible(preflight.FIX_SETUP_MOUSE in needs)
        if all(c.ok for c in checks):
            summary.set_markup("<b>All good — LibreHub is ready.</b>")
        elif preflight.FIX_RELOGIN in needs:
            summary.set_markup("<b>Log out and back in</b> to activate group "
                               "access, then re-check.")
        else:
            summary.set_text("")
        box.show_all()
        b_setup.set_visible(preflight.FIX_PRIVILEGED in needs)
        b_daemon.set_visible(preflight.FIX_START_DAEMON in needs)
        b_restart.set_visible(preflight.FIX_RESTART_DAEMON in needs)
        b_mouse.set_visible(preflight.FIX_SETUP_MOUSE in needs)

    def run_async(fn):
        def work():
            ok, msg = fn()
            GLib.idle_add(lambda: (render(), False)[1])
        threading.Thread(target=work, daemon=True).start()

    b_setup.connect("clicked", lambda _b: run_async(
        preflight.run_privileged_setup))
    b_daemon.connect("clicked", lambda _b: run_async(preflight.start_daemon))
    b_restart.connect("clicked", lambda _b: run_async(preflight.restart_daemon))
    b_mouse.connect("clicked", lambda _b: (show_setup_mouse(dlg), render()))
    dlg.add_button("Re-check", 1)
    dlg.add_button("Close", Gtk.ResponseType.CLOSE)
    dlg.connect("response", lambda _d, r: render() if r == 1 else None)
    render()
    dlg.show_all()
    render()
    while dlg.run() == 1:
        pass
    dlg.destroy()


def main(argv=None) -> int:
    theme.install()
    p = P.load()
    if not C.config_path().exists():
        from . import wizard
        wizard.run_first_run(p)
    win = MainWindow(prefs=p)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    win.present()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
