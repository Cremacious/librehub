from librehub import selection
from librehub.config import Config, Game


def _cfg():
    return Config(version=1, managed_buttons={},
                  games={"1374490": Game("DW", {"KEY_F13": "m"})},
                  default=Game("default", {"KEY_F13": "b"}))


def test_active_bindings_known_game():
    assert selection.active_bindings(_cfg(), "1374490") == {"KEY_F13": "m"}


def test_active_bindings_unknown_game_uses_default():
    assert selection.active_bindings(_cfg(), "999") == {"KEY_F13": "b"}


def test_active_bindings_none_uses_default():
    assert selection.active_bindings(_cfg(), None) == {"KEY_F13": "b"}


def test_resolve_output_hit_and_miss():
    assert selection.resolve_output({"KEY_F13": "m"}, "KEY_F13") == "m"
    assert selection.resolve_output({"KEY_F13": "m"}, "KEY_F14") is None
