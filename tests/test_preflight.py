from librehub import preflight as P
from librehub.preflight import Status


class _Grp:
    def __init__(self, gid, members):
        self.gr_gid = gid
        self.gr_mem = list(members)


def test_packages_ok():
    c = P.check_packages(evdev_ok=True, which=lambda name: "/usr/bin/ratbagctl")
    assert c.status is Status.OK and c.ok


def test_packages_reports_each_missing():
    c = P.check_packages(evdev_ok=False, which=lambda name: None)
    assert c.status is Status.FAIL
    assert "python3-evdev" in c.detail and "ratbagd" in c.detail
    assert c.fix == P.FIX_PRIVILEGED


def test_packages_partial_missing():
    c = P.check_packages(evdev_ok=True, which=lambda name: None)
    assert c.status is Status.FAIL
    assert "ratbagd" in c.detail and "python3-evdev" not in c.detail


def test_uinput_ok():
    c = P.check_uinput(exists=lambda p: True)
    assert c.status is Status.OK


def test_uinput_missing_device():
    c = P.check_uinput(dev_path="/dev/uinput",
                       exists=lambda p: p != "/dev/uinput")
    assert c.status is Status.FAIL and c.fix == P.FIX_PRIVILEGED
    assert "uinput" in c.detail


def test_uinput_missing_rule():
    rule = P.UDEV_RULE
    c = P.check_uinput(exists=lambda p: p != rule)
    assert c.status is Status.FAIL and c.fix == P.FIX_PRIVILEGED
    assert "udev" in c.detail.lower()


def test_input_group_active_is_ok():
    c = P.check_input_group(user="chris", getgroups=lambda: [995],
                            getgrnam=lambda n: _Grp(995, ["chris"]))
    assert c.status is Status.OK


def test_input_group_member_but_not_active_needs_relogin():
    c = P.check_input_group(user="chris", getgroups=lambda: [1000],
                            getgrnam=lambda n: _Grp(995, ["chris"]))
    assert c.status is Status.WARN and c.fix == P.FIX_RELOGIN


def test_input_group_not_a_member_needs_privileged():
    c = P.check_input_group(user="chris", getgroups=lambda: [1000],
                            getgrnam=lambda n: _Grp(995, ["someoneelse"]))
    assert c.status is Status.FAIL and c.fix == P.FIX_PRIVILEGED


def test_input_group_missing_group():
    def _raise(name):
        raise KeyError(name)
    c = P.check_input_group(user="chris", getgroups=lambda: [],
                            getgrnam=_raise)
    assert c.status is Status.FAIL and c.fix == P.FIX_PRIVILEGED


def test_daemon_down():
    c = P.check_daemon(request=lambda: None)
    assert c.status is Status.FAIL and c.fix == P.FIX_START_DAEMON


def test_daemon_running_and_remapping():
    c = P.check_daemon(request=lambda: {"daemon": True, "device": "G502",
                                        "remapping": True})
    assert c.status is Status.OK


def test_daemon_running_but_remapping_inactive():
    c = P.check_daemon(request=lambda: {"daemon": True, "device": "G502",
                                        "remapping": False})
    assert c.status is Status.WARN and c.fix == P.FIX_RESTART_DAEMON


def test_mouse_detected():
    c = P.check_mouse(resolve=lambda: "logitech-g502")
    assert c.status is Status.OK


def test_mouse_absent_is_warn():
    c = P.check_mouse(resolve=lambda: None)
    assert c.status is Status.WARN


def test_mouse_setup_configured():
    c = P.check_mouse_setup({"6": "KEY_F13"})
    assert c.status is Status.OK


def test_mouse_setup_empty_suggests_setup():
    c = P.check_mouse_setup({})
    assert c.status is Status.WARN and c.fix == P.FIX_SETUP_MOUSE


def test_run_privileged_setup_without_pkexec_falls_back_to_instructions():
    ok, msg = P.run_privileged_setup(user="chris", pkexec="",
                                     run=lambda *a, **k: None)
    assert ok is False and "sudo" in msg


def test_run_privileged_setup_success(tmp_path):
    helper = tmp_path / "packaging" / "librehub-setup-privileged.sh"
    helper.parent.mkdir(parents=True)
    helper.write_text("#!/bin/sh\n")

    class _Res:
        returncode = 0
        stdout = "librehub-setup: done"
        stderr = ""

    ok, msg = P.run_privileged_setup(user="chris", helper=helper,
                                     pkexec="/usr/bin/pkexec",
                                     run=lambda *a, **k: _Res())
    assert ok is True and "done" in msg


def test_run_privileged_setup_auth_cancelled(tmp_path):
    helper = tmp_path / "packaging" / "librehub-setup-privileged.sh"
    helper.parent.mkdir(parents=True)
    helper.write_text("#!/bin/sh\n")

    class _Res:
        returncode = 126
        stdout = ""
        stderr = ""

    ok, msg = P.run_privileged_setup(user="chris", helper=helper,
                                     pkexec="/usr/bin/pkexec",
                                     run=lambda *a, **k: _Res())
    assert ok is False and "cancel" in msg.lower()


def test_start_daemon_success():
    class _Res:
        returncode = 0
        stdout = ""
        stderr = ""
    ok, msg = P.start_daemon(run=lambda *a, **k: _Res())
    assert ok is True


def test_start_daemon_failure_surfaces_stderr():
    class _Res:
        returncode = 1
        stdout = ""
        stderr = "Failed to connect to user scope bus"
    ok, msg = P.start_daemon(run=lambda *a, **k: _Res())
    assert ok is False and "user scope" in msg


def test_restart_daemon_success():
    calls = []

    class _Res:
        returncode = 0
        stdout = ""
        stderr = ""

    def _run(args, **k):
        calls.append(args)
        return _Res()

    ok, msg = P.restart_daemon(run=_run)
    assert ok is True
    assert calls == [["systemctl", "--user", "restart", "librehub-daemon"]]


def test_format_report_marks_and_indents_remedies():
    checks = [
        P.Check("a", "Alpha", Status.OK, "fine"),
        P.Check("b", "Beta", Status.FAIL, "broken", "fix it", P.FIX_PRIVILEGED),
    ]
    text = P.format_report(checks)
    assert "[ OK ] Alpha" in text
    assert "[FAIL] Beta" in text
    assert "-> fix it" in text
