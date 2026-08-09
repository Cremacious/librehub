"""System-tray indicator for LibreHub.

Runs in the background with no taskbar window. Provides a tray icon whose
menu opens the editor, restarts the daemon, or quits the tray. Tries the
best available backend for the desktop: XApp (Cinnamon/Mint native), then
Ayatana AppIndicator3, then the legacy GtkStatusIcon.
"""
from __future__ import annotations

import subprocess
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from . import gui  # noqa: E402

ICON_NAME = "input-mouse"


class Tray:
    def __init__(self):
        self._editor: gui.Window | None = None
        self._backend = None
        for setup in (self._try_xapp, self._try_appindicator,
                      self._try_statusicon):
            try:
                if setup():
                    break
            except Exception:  # noqa: BLE001 - any backend failure -> try next
                continue
        if self._backend is None:
            raise RuntimeError("no system tray backend available")

    # --- actions ---
    def open_editor(self, *_args):
        if self._editor is not None:
            try:
                self._editor.present()
                return
            except Exception:  # noqa: BLE001 - window was destroyed
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

    # --- backends ---
    def _try_xapp(self) -> bool:
        gi.require_version("XApp", "1.0")
        from gi.repository import XApp
        icon = XApp.StatusIcon()
        icon.set_icon_name(ICON_NAME)
        icon.set_tooltip_text("LibreHub")
        icon.set_primary_menu(self._menu())
        icon.set_secondary_menu(self._menu())
        self._backend = icon
        return True

    def _try_appindicator(self) -> bool:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AI
        ind = AI.Indicator.new("librehub", ICON_NAME,
                               AI.IndicatorCategory.APPLICATION_STATUS)
        ind.set_status(AI.IndicatorStatus.ACTIVE)
        ind.set_title("LibreHub")
        ind.set_menu(self._menu())
        self._backend = ind
        return True

    def _try_statusicon(self) -> bool:
        icon = Gtk.StatusIcon()
        icon.set_from_icon_name(ICON_NAME)
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
        tray = Tray()  # keep a reference alive for the whole main loop
    except RuntimeError as e:
        print(f"LibreHub tray: {e}", file=sys.stderr)
        return 1
    assert tray is not None
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
