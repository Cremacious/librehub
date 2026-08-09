import pytest
from librehub import keys


def test_single_letter():
    from evdev import ecodes
    assert keys.to_code("m") == ecodes.KEY_M


def test_digit():
    from evdev import ecodes
    assert keys.to_code("4") == ecodes.KEY_4


def test_alias_space():
    from evdev import ecodes
    assert keys.to_code("space") == ecodes.KEY_SPACE


def test_explicit_keyname():
    from evdev import ecodes
    assert keys.to_code("KEY_F13") == ecodes.KEY_F13


def test_unknown_raises():
    with pytest.raises(ValueError):
        keys.to_code("nope-not-a-key")


def test_fsignals_are_twelve_and_valid():
    assert len(keys.FSIGNALS) == 12
    for name in keys.FSIGNALS:
        assert keys.to_code(name) > 0
