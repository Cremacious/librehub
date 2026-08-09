import pytest
from librehub import ratbag


class FakeRun:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode
        self.calls = []

    def __call__(self, args, **kw):
        self.calls.append(args)
        class R:  # noqa: D401 - simple stub
            pass
        r = R()
        r.stdout = self.stdout
        r.returncode = self.returncode
        return r


def test_resolve_device_matches_model():
    fr = FakeRun(stdout="hollering-marmot:    Logitech G502 HERO Gaming Mouse \n")
    assert ratbag.resolve_device("G502 HERO", run=fr) == "hollering-marmot"


def test_resolve_device_no_match():
    fr = FakeRun(stdout="whatever:    Some Other Mouse\n")
    assert ratbag.resolve_device("G502 HERO", run=fr) is None


def test_parse_buttons():
    info = (
        "Profile 0:\n"
        "  Button: 0 is mapped to 'button 1'\n"
        "  Button: 6 is mapped to macro '↕M'\n"
        "Profile 1: (active)\n"
        "  Button: 6 is mapped to macro '↕J'\n"
    )
    got = ratbag.parse_buttons(info)
    # only the (active) profile's buttons
    assert got[6] == "macro '↕J'"


def test_assign_signal_builds_command():
    fr = FakeRun()
    ratbag.assign_signal("dev0", 0, 6, "KEY_F13", run=fr)
    assert fr.calls[-1] == ["ratbagctl", "dev0", "profile", "0", "button", "6",
                            "action", "set", "macro", "KEY_F13"]


def test_assign_signal_raises_on_failure():
    fr = FakeRun(returncode=1)
    with pytest.raises(ratbag.RatbagError):
        ratbag.assign_signal("dev0", 0, 6, "KEY_F13", run=fr)


MULTI_PROFILE_INFO = (
    "Profile 0:\n"
    "  Button: 0 is mapped to 'button 1'\n"
    "  Button: 1 is mapped to 'button 2'\n"
    "  Button: 6 is mapped to macro '↕M'\n"
    "Profile 1: (active)\n"
    "  Button: 0 is mapped to 'button 1'\n"
    "  Button: 1 is mapped to 'button 2'\n"
    "  Button: 6 is mapped to macro '↕J'\n"
)


def test_parse_profile_buttons_selects_requested_profile():
    got0 = ratbag.parse_profile_buttons(MULTI_PROFILE_INFO, 0)
    got1 = ratbag.parse_profile_buttons(MULTI_PROFILE_INFO, 1)
    assert got0[6] == "macro '↕M'"
    assert got1[6] == "macro '↕J'"
    assert got0[6] != got1[6]


def test_parse_profile_buttons_missing_profile_returns_empty():
    assert ratbag.parse_profile_buttons(MULTI_PROFILE_INFO, 2) == {}


def test_next_free_signals_empty_used():
    assert ratbag.next_free_signals([], 3) == ["KEY_F13", "KEY_F14", "KEY_F15"]


def test_next_free_signals_skips_used():
    assert ratbag.next_free_signals(["KEY_F13"], 2) == ["KEY_F14", "KEY_F15"]


def test_next_free_signals_raises_when_exhausted():
    used = [f"KEY_F{n}" for n in range(13, 25)]
    with pytest.raises(ratbag.RatbagError):
        ratbag.next_free_signals(used, 1)


def test_device_info_builds_command_and_returns_stdout():
    fr = FakeRun(stdout="Profile 0:\n  Button: 0 is mapped to 'button 1'\n")
    out = ratbag.device_info("dev0", run=fr)
    assert fr.calls[-1] == ["ratbagctl", "dev0", "info"]
    assert out == "Profile 0:\n  Button: 0 is mapped to 'button 1'\n"


def test_device_info_raises_on_failure():
    fr = FakeRun(returncode=1)
    with pytest.raises(ratbag.RatbagError):
        ratbag.device_info("dev0", run=fr)


def test_signals_in_use_detects_fsignal_macros():
    buttons = {6: "macro '↕F13'", 7: "macro '↕F14'", 0: "'button 1'"}
    assert ratbag.signals_in_use(buttons) == {"KEY_F13", "KEY_F14"}


def test_signals_in_use_none_present():
    buttons = {0: "'button 1'", 1: "'button 2'"}
    assert ratbag.signals_in_use(buttons) == set()


def test_plan_signal_assignment_fresh():
    final, new = ratbag.plan_signal_assignment(
        previously_managed={}, checked=[6, 7], reserved=set())
    assert final == {"6": "KEY_F13", "7": "KEY_F14"}
    assert new == {6: "KEY_F13", 7: "KEY_F14"}


def test_plan_signal_assignment_kept_retains_code():
    final, new = ratbag.plan_signal_assignment(
        previously_managed={"6": "KEY_F13"}, checked=[6, 7],
        reserved={"KEY_F13"})
    assert final == {"6": "KEY_F13", "7": "KEY_F14"}
    assert new == {7: "KEY_F14"}


def test_plan_signal_assignment_orphan_not_reused():
    final, new = ratbag.plan_signal_assignment(
        previously_managed={}, checked=[9], reserved={"KEY_F13"})
    assert final == {"9": "KEY_F14"}
    assert new == {9: "KEY_F14"}


def test_plan_signal_assignment_exhaustion_propagates():
    reserved = {f"KEY_F{n}" for n in range(13, 25)}
    with pytest.raises(ratbag.RatbagError):
        ratbag.plan_signal_assignment(
            previously_managed={}, checked=[0], reserved=reserved)
