from librehub import focus


def test_parse_window_id():
    out = "_NET_ACTIVE_WINDOW(WINDOW): window id # 0x8a00021\n"
    assert focus.parse_window_id(out) == "0x8a00021"


def test_parse_window_id_none():
    assert focus.parse_window_id("_NET_ACTIVE_WINDOW(WINDOW): window id # 0x0\n") is None
    assert focus.parse_window_id("") is None


def test_parse_wm_pid():
    assert focus.parse_wm_pid("_NET_WM_PID(CARDINAL) = 50841\n") == 50841


def test_parse_wm_pid_none():
    assert focus.parse_wm_pid("no pid here") is None


def test_appid_from_environ():
    env = b"PATH=/usr/bin\x00SteamAppId=1374490\x00HOME=/home/chris\x00"
    assert focus.appid_from_environ(env) == "1374490"


def test_appid_from_environ_absent():
    assert focus.appid_from_environ(b"PATH=/usr/bin\x00") is None
