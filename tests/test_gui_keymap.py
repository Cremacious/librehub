import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk

from librehub import gui


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


def test_parse_library_paths_multiple():
    vdf = '''
    "libraryfolders"
    {
        "0"
        {
            "path"		"/home/chris/.local/share/Steam"
        }
        "1"
        {
            "path"		"/mnt/games/SteamLibrary"
        }
    }
    '''
    assert gui.parse_library_paths(vdf) == [
        "/home/chris/.local/share/Steam", "/mnt/games/SteamLibrary"]


def test_parse_library_paths_none():
    assert gui.parse_library_paths("garbage without paths") == []


def test_button_label_known_index():
    assert gui.button_label("KEY_F20", {"4": "KEY_F20", "5": "KEY_F21"}) \
        == "Button 4"


def test_button_label_unknown_falls_back_to_code():
    assert gui.button_label("KEY_F13", {}) == "F13"


def test_valid_appid_is_digits():
    assert gui.is_valid_appid("1086940")


def test_valid_appid_ignores_surrounding_whitespace():
    assert gui.is_valid_appid("  1086940 ")


def test_empty_appid_is_invalid():
    assert not gui.is_valid_appid("")
    assert not gui.is_valid_appid("   ")


def test_non_numeric_appid_is_invalid():
    assert not gui.is_valid_appid("baldurs gate")
    assert not gui.is_valid_appid("108694a")


def test_appid_with_inner_space_is_invalid():
    assert not gui.is_valid_appid("108 6940")
