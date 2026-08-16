from __future__ import annotations

import subprocess
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from . import gui, theme

FALLBACK_ICON_NAME = "input-mouse"


def icon_name(theme_lookup=None) -> str:
    lookup = theme_lookup or Gtk.IconTheme.get_default()
    return (theme.ICON_NAME if lookup.has_icon(theme.ICON_NAME)
            else FALLBACK_ICON_NAME)


class Tray:
    def __init__(self):
        self._editor: gui.Window | None = None
        self._backend = None
        for setup in (self._try_xapp, self._try_appindicator,
                      self._try_statusicon):
            try:
                if setup():
                    break
            except Exception:
                continue
        if self._backend is None:
            raise RuntimeError("no system tray backend available")

    def open_editor(self, *_args):
        if self._editor is not None:
            try:
                self._editor.present()
                return
            except Exception:
                self._editor = None
        win = gui.Window()
        win.connect("destroy", self._on_editor_closed)
        win.show_all()
        win.present()
        self._editor = win

    def _on_editor_closed(self, *_args):
        self._editor = None

    def restart_daemon(self, *_args):
        subprocess.run(["systemctl", "--user", "restart", "librehub-daemon"],
                       check=False)

    def quit(self, *_args):
        Gtk.main_quit()

    def _menu(self) -> Gtk.Menu:
        menu = Gtk.Menu()
        for label, callback in (("Open editor", self.open_editor),
                                ("Restart daemon", self.restart_daemon),
                                ("Quit LibreHub tray", self.quit)):
            item = Gtk.MenuItem(label=label)
            item.connect("activate", callback)
            menu.append(item)
        menu.show_all()
        return menu

    def _try_xapp(self) -> bool:
        gi.require_version("XApp", "1.0")
        from gi.repository import XApp
        icon = XApp.StatusIcon()
        icon.set_icon_name(icon_name())
        icon.set_tooltip_text("LibreHub")
        icon.set_primary_menu(self._menu())
        icon.set_secondary_menu(self._menu())
        self._backend = icon
        return True

    def _try_appindicator(self) -> bool:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AI
        ind = AI.Indicator.new("librehub", icon_name(),
                               AI.IndicatorCategory.APPLICATION_STATUS)
        ind.set_status(AI.IndicatorStatus.ACTIVE)
        ind.set_title("LibreHub")
        ind.set_menu(self._menu())
        self._backend = ind
        return True

    def _try_statusicon(self) -> bool:
        icon = Gtk.StatusIcon()
        icon.set_from_icon_name(icon_name())
        icon.set_tooltip_text("LibreHub")
        menu = self._menu()
        icon.connect("activate", self.open_editor)
        icon.connect(
            "popup-menu",
            lambda _i, button, time: menu.popup(
                None, None, None, None, button, time))
        self._backend = icon
        return True


def main(argv=None) -> int:
    try:
        tray = Tray()
    except RuntimeError as e:
        print(f"LibreHub tray: {e}", file=sys.stderr)
        return 1
    assert tray is not None
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
