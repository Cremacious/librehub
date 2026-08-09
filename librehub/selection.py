"""Pure logic for selecting the active binding set."""
from __future__ import annotations

from .config import Config


def active_bindings(config: Config, appid: str | None) -> dict[str, str]:
    if appid is not None and appid in config.games:
        return config.games[appid].bindings
    return config.default.bindings


def resolve_output(bindings: dict[str, str], fcode: str) -> str | None:
    return bindings.get(fcode)
