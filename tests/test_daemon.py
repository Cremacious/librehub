from pathlib import Path
from librehub import daemon, config as C, ratbag


class SpyEngine:
    def __init__(self):
        self.bindings = None

    def set_bindings(self, b):
        self.bindings = b


def _write_cfg(p: Path, appid="1374490", out="m"):
    cfg = C.Config(version=1, managed_buttons={"6": "KEY_F13"},
                   games={appid: C.Game("DW", {"KEY_F13": out})},
                   default=C.Game("default", {}))
    C.save(cfg, p)


def test_apply_appid_sets_game_bindings(tmp_path: Path):
    p = tmp_path / "config.json"
    _write_cfg(p)
    eng = SpyEngine()
    d = daemon.Daemon(cfg_path=p, engine=eng, appid_fn=lambda: None, model="X")
    d.reload_config()
    d.apply_appid("1374490")
    assert eng.bindings == {"KEY_F13": "m"}
    assert d.active_appid == "1374490"


def test_apply_appid_unknown_uses_default(tmp_path: Path):
    p = tmp_path / "config.json"
    _write_cfg(p)
    eng = SpyEngine()
    d = daemon.Daemon(cfg_path=p, engine=eng, appid_fn=lambda: None, model="X")
    d.reload_config()
    d.apply_appid("999")
    assert eng.bindings == {}


def test_reload_keeps_last_good_on_bad_config(tmp_path: Path):
    p = tmp_path / "config.json"
    _write_cfg(p)
    eng = SpyEngine()
    d = daemon.Daemon(cfg_path=p, engine=eng, appid_fn=lambda: None, model="X")
    d.reload_config()
    p.write_text("{ not valid json")
    d.reload_config()  # should not raise
    d.apply_appid("1374490")
    assert eng.bindings == {"KEY_F13": "m"}


def test_resolve_signal_device_survives_ratbag_error(tmp_path: Path, monkeypatch):
    p = tmp_path / "config.json"
    _write_cfg(p)
    eng = SpyEngine()
    d = daemon.Daemon(cfg_path=p, engine=eng, appid_fn=lambda: None, model=None)

    def _raise(model):
        raise ratbag.RatbagError("ratbagctl not found")

    monkeypatch.setattr(daemon.ratbag, "resolve_device", _raise)

    result = d._resolve_signal_device()

    assert result is None


def test_resolve_signal_device_returns_found_path(tmp_path: Path, monkeypatch):
    p = tmp_path / "config.json"
    _write_cfg(p)
    eng = SpyEngine()
    d = daemon.Daemon(cfg_path=p, engine=eng, appid_fn=lambda: None, model=None)

    monkeypatch.setattr(daemon.ratbag, "resolve_device", lambda model: "dev0")
    monkeypatch.setattr(daemon.ratbag, "device_name", lambda dev: "Some Mouse")
    monkeypatch.setattr(daemon.E, "find_signal_device", lambda model: "/dev/input/event9")

    result = d._resolve_signal_device()

    assert result == "/dev/input/event9"
    assert d.model == "Some Mouse"
