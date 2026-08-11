from librehub import prefs as P


def test_defaults_when_missing(tmp_path):
    p = P.load(tmp_path / "nope.json")
    assert p.keep_above is True
    assert p.appearance == "system"


def test_round_trip(tmp_path):
    path = tmp_path / "prefs.json"
    P.save(P.Prefs(keep_above=False, start_at_login=False, tray_icon=True,
                   appearance="dark"), path)
    got = P.load(path)
    assert got.keep_above is False
    assert got.tray_icon is True
    assert got.appearance == "dark"


def test_bad_appearance_normalized(tmp_path):
    path = tmp_path / "prefs.json"
    path.write_text('{"appearance": "neon"}')
    assert P.load(path).appearance == "system"


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "prefs.json"
    path.write_text("{ not json")
    assert P.load(path).appearance == "system"
