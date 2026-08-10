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


def test_running_appids_dedup_first_seen_order():
    envs = {
        10: b"SteamAppId=552500\x00",
        11: b"SteamAppId=1374490\x00",
        12: b"SteamAppId=552500\x00",
    }
    assert focus.running_appids(pids=[10, 11, 12], read_environ=envs.get) == [
        "552500", "1374490"]


def test_running_appids_none_running():
    envs = {10: b"PATH=/usr/bin\x00", 11: b""}
    assert focus.running_appids(pids=[10, 11], read_environ=envs.get) == []


def test_running_appids_tolerates_read_error():
    def flaky_read_environ(pid):
        if pid == 11:
            raise OSError("no such process")
        return {10: b"SteamAppId=552500\x00", 12: b"SteamAppId=1374490\x00"}[pid]

    assert focus.running_appids(pids=[10, 11, 12],
                                 read_environ=flaky_read_environ) == [
        "552500", "1374490"]


def test_is_wayland_by_session_type():
    assert focus.is_wayland(environ={"XDG_SESSION_TYPE": "wayland"}) is True


def test_is_wayland_by_wayland_display():
    assert focus.is_wayland(environ={"WAYLAND_DISPLAY": "wayland-0"}) is True


def test_is_wayland_by_socket(tmp_path):
    # A systemd --user service lacks the env vars but the socket is present.
    (tmp_path / "wayland-0").write_text("")
    assert focus.is_wayland(environ={}, runtime_dir=str(tmp_path)) is True


def test_is_wayland_false_on_x11(tmp_path):
    assert focus.is_wayland(environ={"XDG_SESSION_TYPE": "x11"},
                            runtime_dir=str(tmp_path)) is False


def test_single_running_known_appid_exactly_one():
    assert focus.single_running_known_appid(
        {"1374490", "552500"}, running=["1374490"]) == "1374490"


def test_single_running_known_appid_none_when_ambiguous():
    assert focus.single_running_known_appid(
        {"1374490", "552500"}, running=["1374490", "552500"]) is None


def test_single_running_known_appid_none_when_no_match():
    assert focus.single_running_known_appid(
        {"1374490"}, running=["999999"]) is None


def test_single_running_known_appid_empty_config():
    assert focus.single_running_known_appid(set(), running=["1374490"]) is None
