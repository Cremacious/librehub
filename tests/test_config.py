import json
import pytest
from pathlib import Path
from librehub import config as C


def test_default_config_is_valid():
    cfg = C.default_config()
    assert cfg.version == 1
    assert cfg.games == {}
    assert cfg.default.bindings == {}


def test_save_then_load_roundtrip(tmp_path: Path):
    cfg = C.Config(
        version=1,
        managed_buttons={"6": "KEY_F13"},
        games={"1374490": C.Game(name="Dragonwilds", bindings={"KEY_F13": "m"})},
        default=C.Game(name="default", bindings={}),
    )
    p = tmp_path / "config.json"
    C.save(cfg, p)
    loaded = C.load(p)
    assert loaded == cfg


def test_save_creates_parent_dirs(tmp_path: Path):
    p = tmp_path / "nested" / "dir" / "config.json"
    C.save(C.default_config(), p)
    assert p.exists()


def test_load_rejects_bad_fcode(tmp_path: Path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({
        "version": 1, "managed_buttons": {},
        "games": {"1": {"name": "x", "bindings": {"KEY_A": "m"}}},
        "default": {"name": "default", "bindings": {}},
    }))
    with pytest.raises(C.ConfigError):
        C.load(p)


def test_load_rejects_unknown_output_key(tmp_path: Path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({
        "version": 1, "managed_buttons": {},
        "games": {"1": {"name": "x", "bindings": {"KEY_F13": "not-a-key"}}},
        "default": {"name": "default", "bindings": {}},
    }))
    with pytest.raises(C.ConfigError):
        C.load(p)


def test_load_missing_file_raises(tmp_path: Path):
    with pytest.raises(C.ConfigError):
        C.load(tmp_path / "does-not-exist.json")
