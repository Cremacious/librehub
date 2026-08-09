"""Config data model and persistence for LibreHub."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import keys


class ConfigError(Exception):
    pass


@dataclass
class Game:
    name: str
    bindings: dict[str, str] = field(default_factory=dict)


@dataclass
class Config:
    version: int
    managed_buttons: dict[str, str]
    games: dict[str, Game]
    default: Game


def default_config() -> Config:
    return Config(version=1, managed_buttons={}, games={},
                  default=Game(name="default", bindings={}))


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "librehub" / "config.json"


def _validate_bindings(bindings: dict) -> None:
    for fcode, out in bindings.items():
        if fcode not in keys.FSIGNALS:
            raise ConfigError(f"binding key {fcode!r} is not a valid signal (KEY_F13..KEY_F24)")
        try:
            keys.to_code(out)
        except ValueError as e:
            raise ConfigError(f"binding output {out!r} is not a valid key: {e}") from e


def _game_from_dict(d: dict) -> Game:
    if not isinstance(d, dict) or "bindings" not in d:
        raise ConfigError("game entry must have a 'bindings' object")
    _validate_bindings(d["bindings"])
    return Game(name=str(d.get("name", "")), bindings=dict(d["bindings"]))


def load(path: Path) -> Config:
    try:
        raw = json.loads(Path(path).read_text())
    except FileNotFoundError as e:
        raise ConfigError(f"config not found: {path}") from e
    except json.JSONDecodeError as e:
        raise ConfigError(f"config is not valid JSON: {e}") from e
    try:
        version = int(raw["version"])
        managed = {str(k): str(v) for k, v in raw.get("managed_buttons", {}).items()}
        games = {str(aid): _game_from_dict(g) for aid, g in raw.get("games", {}).items()}
        default = _game_from_dict(raw.get("default", {"name": "default", "bindings": {}}))
    except (KeyError, TypeError, ValueError) as e:
        raise ConfigError(f"malformed config: {e}") from e
    return Config(version=version, managed_buttons=managed, games=games, default=default)


def _game_to_dict(g: Game) -> dict:
    return {"name": g.name, "bindings": g.bindings}


def save(config: Config, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": config.version,
        "managed_buttons": config.managed_buttons,
        "games": {aid: _game_to_dict(g) for aid, g in config.games.items()},
        "default": _game_to_dict(config.default),
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)  # atomic
