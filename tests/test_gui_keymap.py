"""Tests for the pure key-capture helpers in the GUI module.

Importing librehub.gui pulls in GTK/GDK, but these helpers don't need a
display — only the keyval constants and keyval->unicode translation.
"""
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk  # noqa: E402

from librehub import gui  # noqa: E402


def test_keyval_space():
    assert gui.key_name_from_keyval(Gdk.KEY_space) == "space"


def test_keyval_letter():
    assert gui.key_name_from_keyval(Gdk.KEY_r) == "r"


def test_keyval_letter_shifted():
    assert gui.key_name_from_keyval(Gdk.KEY_R) == "r"


def test_keyval_digit():
    assert gui.key_name_from_keyval(Gdk.KEY_4) == "4"


def test_keyval_return():
    assert gui.key_name_from_keyval(Gdk.KEY_Return) == "enter"


def test_keyval_fkey():
    assert gui.key_name_from_keyval(Gdk.KEY_F1) == "f1"
    assert gui.key_name_from_keyval(Gdk.KEY_F5) == "f5"


def test_keyval_arrow():
    assert gui.key_name_from_keyval(Gdk.KEY_Up) == "up"


def test_keyval_unsupported():
    assert gui.key_name_from_keyval(Gdk.KEY_Menu) is None


def test_pretty_space():
    assert gui.pretty_key("space") == "Spacebar"


def test_pretty_letter():
    assert gui.pretty_key("r") == "R"


def test_pretty_fkey():
    assert gui.pretty_key("f1") == "F1"
