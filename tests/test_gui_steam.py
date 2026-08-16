from pathlib import Path

import pytest

from librehub import config as C
from librehub import gui


def _manifest(steamapps: Path, appid: str, name: str) -> None:
    steamapps.mkdir(parents=True, exist_ok=True)
    (steamapps / f"appmanifest_{appid}.acf").write_text(
        '"AppState"\n{\n\t"appid"\t\t"%s"\n\t"name"\t\t"%s"\n}\n'
        % (appid, name))


def _library_vdf(steamapps: Path, paths: list[str]) -> None:
    steamapps.mkdir(parents=True, exist_ok=True)
    blocks = "\n".join(
        '\t"%d"\n\t{\n\t\t"path"\t\t"%s"\n\t}' % (i, p)
        for i, p in enumerate(paths))
    (steamapps / "libraryfolders.vdf").write_text(
        '"libraryfolders"\n{\n%s\n}\n' % blocks)


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def test_steam_roots_includes_native_install(home):
    assert home / ".local" / "share" / "Steam" in gui._steam_roots()


def test_steam_roots_includes_flatpak_install(home):
    flatpak = home / ".var" / "app" / "com.valvesoftware.Steam"
    assert flatpak / "data" / "Steam" in gui._steam_roots()


def test_steamapps_dirs_deduplicates_aliased_roots(home):
    real = home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" \
        / "share" / "Steam"
    real.mkdir(parents=True)
    alias = home / ".var" / "app" / "com.valvesoftware.Steam" / "data"
    alias.mkdir(parents=True)
    (alias / "Steam").symlink_to(real)

    dirs = gui._steamapps_dirs()
    resolved = [d.resolve() for d in dirs]
    assert len(resolved) == len(set(resolved))


def test_resolve_game_name_from_flatpak_manifest(home):
    steamapps = (home / ".var" / "app" / "com.valvesoftware.Steam" / "data"
                 / "Steam" / "steamapps")
    _manifest(steamapps, "1070560", "Teenage Mutant Ninja Turtles")

    assert gui._resolve_game_name("1070560") == \
        "Teenage Mutant Ninja Turtles"


def test_resolve_game_name_from_flatpak_secondary_library(home, tmp_path):
    library = tmp_path / "mnt" / "games" / "SteamLibrary"
    _manifest(library / "steamapps", "1086940", "Baldur's Gate 3")
    flatpak = (home / ".var" / "app" / "com.valvesoftware.Steam" / "data"
               / "Steam" / "steamapps")
    _library_vdf(flatpak, [str(library)])

    assert gui._resolve_game_name("1086940") == "Baldur's Gate 3"


def test_resolve_game_name_falls_back_to_appid(home):
    assert gui._resolve_game_name("353454") == "Game 353454"


def test_initial_name_uses_the_steam_manifest_for_a_new_game(home):
    steamapps = (home / ".var" / "app" / "com.valvesoftware.Steam" / "data"
                 / "Steam" / "steamapps")
    _manifest(steamapps, "1086940", "Baldur's Gate 3")

    assert gui._initial_game_name({}, "1086940") == "Baldur's Gate 3"


def test_initial_name_keeps_the_name_an_existing_profile_already_has(home):
    steamapps = (home / ".var" / "app" / "com.valvesoftware.Steam" / "data"
                 / "Steam" / "steamapps")
    _manifest(steamapps, "1086940", "Baldur's Gate 3")
    games = {"1086940": C.Game(name="BG3", bindings={})}

    assert gui._initial_game_name(games, "1086940") == "BG3"
