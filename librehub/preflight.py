from __future__ import annotations

import getpass
import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from . import ipc

UDEV_RULE = "/etc/udev/rules.d/99-librehub-uinput.rules"
UINPUT_DEV = "/dev/uinput"
INPUT_GROUP = "input"

FIX_PRIVILEGED = "privileged"
FIX_START_DAEMON = "start_daemon"
FIX_RESTART_DAEMON = "restart_daemon"
FIX_SETUP_MOUSE = "setup_mouse"
FIX_RELOGIN = "relogin"


class Status(Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class Check:
    key: str
    title: str
    status: Status
    detail: str
    remedy: str = ""
    fix: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is Status.OK


def _current_user() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USER", "")


def _evdev_importable() -> bool:
    try:
        import evdev
    except Exception:
        return False
    return evdev is not None


def check_packages(evdev_ok: bool | None = None, which=shutil.which) -> Check:
    evdev_ok = _evdev_importable() if evdev_ok is None else evdev_ok
    missing = []
    if not evdev_ok:
        missing.append("python3-evdev")
    if which("ratbagctl") is None:
        missing.append("ratbagd")
    if missing:
        return Check("packages", "System packages", Status.FAIL,
                     "missing: " + ", ".join(missing),
                     "Install the required system packages.", FIX_PRIVILEGED)
    return Check("packages", "System packages", Status.OK,
                 "python3-evdev and ratbagd present")


def check_uinput(rule_path: str = UDEV_RULE, dev_path: str = UINPUT_DEV,
                 exists=os.path.exists) -> Check:
    if not exists(dev_path):
        return Check("uinput", "Virtual keyboard (/dev/uinput)", Status.FAIL,
                     "/dev/uinput is missing",
                     "Install the udev rule (it loads the uinput module).",
                     FIX_PRIVILEGED)
    if not exists(rule_path):
        return Check("uinput", "Virtual keyboard (/dev/uinput)", Status.FAIL,
                     "LibreHub udev rule not installed",
                     "Install the udev rule so the daemon may write to "
                     "/dev/uinput.", FIX_PRIVILEGED)
    return Check("uinput", "Virtual keyboard (/dev/uinput)", Status.OK,
                 "udev rule installed and /dev/uinput present")


def check_input_group(user: str | None = None, getgroups=os.getgroups,
                      getgrnam=None) -> Check:
    if getgrnam is None:
        import grp
        getgrnam = grp.getgrnam
    user = user or _current_user()
    try:
        gr = getgrnam(INPUT_GROUP)
    except KeyError:
        return Check("input_group", "Input group", Status.FAIL,
                     "the 'input' group does not exist",
                     "Run system setup to create and join it.", FIX_PRIVILEGED)
    active = gr.gr_gid in getgroups()
    member = user in gr.gr_mem
    if active:
        return Check("input_group", "Input group", Status.OK,
                     f"'{user}' is in 'input' and it is active this session")
    if member:
        return Check("input_group", "Input group", Status.WARN,
                     "you're in 'input', but this login session predates it",
                     "Log out and back in (or reboot) to activate it.",
                     FIX_RELOGIN)
    return Check("input_group", "Input group", Status.FAIL,
                 f"'{user}' is not in the 'input' group",
                 "Run system setup to add you to it.", FIX_PRIVILEGED)


def check_daemon(request=None) -> Check:
    st = (request or status_request)()
    if not st or not st.get("daemon"):
        return Check("daemon", "Daemon", Status.FAIL, "not reachable",
                     "Start the LibreHub daemon.", FIX_START_DAEMON)
    if st.get("remapping"):
        return Check("daemon", "Daemon", Status.OK,
                     f"running · device: {st.get('device')} · remapping active")
    return Check("daemon", "Daemon", Status.WARN,
                 f"running, but remapping is inactive "
                 f"(device: {st.get('device') or 'none'})",
                 "Restart the daemon so it picks up 'input' group access and "
                 "your mouse setup. (If the group check above says re-login, "
                 "do that first.)",
                 FIX_RESTART_DAEMON)


def check_mouse(resolve=None) -> Check:
    from . import ratbag
    resolve = resolve or ratbag.resolve_device
    try:
        dev = resolve()
    except Exception as e:
        return Check("mouse", "Mouse", Status.WARN, f"detection failed: {e}",
                     "Ensure ratbagd is running and a supported mouse is "
                     "plugged in.")
    if dev:
        return Check("mouse", "Mouse", Status.OK, f"detected ({dev})")
    return Check("mouse", "Mouse", Status.WARN, "no supported mouse found",
                 "Plug in a Logitech/ratbagd-supported mouse.")


def check_mouse_setup(managed_buttons) -> Check:
    if managed_buttons:
        return Check("mouse_setup", "Mouse buttons", Status.OK,
                     f"{len(managed_buttons)} button(s) configured")
    return Check("mouse_setup", "Mouse buttons", Status.WARN,
                 "no buttons assigned yet",
                 "Click 'Set up mouse' to assign F13–F24 signals to the "
                 "buttons you want to remap.", FIX_SETUP_MOUSE)


def run_all(managed_buttons=None) -> list[Check]:
    return [
        check_packages(),
        check_uinput(),
        check_input_group(),
        check_daemon(),
        check_mouse(),
        check_mouse_setup(managed_buttons or {}),
    ]


def status_request(timeout: float = 1.5) -> dict | None:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(ipc.socket_path())
        s.sendall(ipc.encode({"cmd": "status"}))
        line = s.makefile("rb").readline()
        s.close()
        return ipc.decode(line)
    except (OSError, ValueError):
        return None


def privileged_helper_path() -> Path:
    return (Path(__file__).resolve().parent.parent
            / "packaging" / "librehub-setup-privileged.sh")


def run_privileged_setup(user: str | None = None, helper: Path | None = None,
                         pkexec: str | None = None,
                         run=subprocess.run) -> tuple[bool, str]:
    user = user or _current_user()
    helper = helper or privileged_helper_path()
    repo_dir = str(helper.resolve().parent.parent)
    pk = pkexec if pkexec is not None else shutil.which("pkexec")
    if not pk:
        return False, ("pkexec was not found. Install the 'policykit-1' "
                       "package, or run this in a terminal:\n"
                       f"  sudo {helper} {repo_dir} {user}")
    if not helper.exists():
        return False, f"setup helper not found at {helper}"
    try:
        res = run([pk, str(helper), repo_dir, user],
                  capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"could not launch setup: {e}"
    out = ((res.stdout or "") + (res.stderr or "")).strip()
    if res.returncode == 0:
        return True, out or "System setup complete."
    if res.returncode in (126, 127):
        return False, "Authorization was cancelled or failed."
    return False, out or f"setup failed (exit code {res.returncode})."


def start_daemon(run=subprocess.run) -> tuple[bool, str]:
    try:
        res = run(["systemctl", "--user", "enable", "--now",
                   "librehub-daemon"], capture_output=True, text=True,
                  timeout=15)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"could not start daemon: {e}"
    if res.returncode == 0:
        return True, "Daemon started."
    return False, (res.stderr or "").strip() or f"exit code {res.returncode}"


def restart_daemon(run=subprocess.run) -> tuple[bool, str]:
    try:
        res = run(["systemctl", "--user", "restart", "librehub-daemon"],
                  capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"could not restart daemon: {e}"
    if res.returncode == 0:
        return True, "Daemon restarted."
    return False, (res.stderr or "").strip() or f"exit code {res.returncode}"


def format_report(checks) -> str:
    sym = {Status.OK: "[ OK ]", Status.WARN: "[WARN]", Status.FAIL: "[FAIL]"}
    lines = []
    for c in checks:
        lines.append(f"{sym[c.status]} {c.title}: {c.detail}")
        if not c.ok and c.remedy:
            lines.append(f"         -> {c.remedy}")
    return "\n".join(lines)


def main(argv=None) -> int:
    from . import config as C
    try:
        managed = C.load(C.config_path()).managed_buttons
    except C.ConfigError:
        managed = {}
    checks = run_all(managed)
    print(format_report(checks))
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
