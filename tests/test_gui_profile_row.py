import gi
import pytest

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from librehub import gui

pytestmark = pytest.mark.skipif(not Gtk.init_check()[0],
                                reason="needs a display")


class _StubWindow:

    def open_row_menu(self, row):
        pass

    def commit_rename(self, pid, new_name):
        pass


def _shown_row(pid, name, is_default):
    row = gui.ProfileRow(_StubWindow(), pid, name, is_default)
    lst = Gtk.ListBox()
    lst.add(row)
    win = Gtk.OffscreenWindow()
    win.add(lst)
    win.show_all()
    return row


def test_overflow_icon_is_visible_on_a_game_row():
    row = _shown_row("1086940", "Baldur's Gate 3", is_default=False)

    assert row.overflow.get_visible()
    assert row.overflow.get_child().get_visible()


def test_default_row_has_no_overflow_button():
    row = _shown_row("default", "All other games", is_default=True)

    assert row.overflow is None


def test_row_shows_no_binding_count():
    row = _shown_row("1086940", "Baldur's Gate 3", is_default=False)

    labels = []

    def walk(w):
        if isinstance(w, Gtk.Label):
            labels.append(w.get_text())
        if isinstance(w, Gtk.Container):
            for ch in w.get_children():
                walk(ch)
    walk(row)

    assert labels == ["B", "Baldur's Gate 3", "1086940"]
