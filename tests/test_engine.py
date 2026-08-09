from librehub import engine


class FakeUInput:
    def __init__(self):
        self.events = []
        self.synced = 0

    def write(self, etype, code, value):
        self.events.append((etype, code, value))

    def syn(self):
        self.synced += 1


def test_mapped_button_down_injects_key():
    from evdev import ecodes
    ui = FakeUInput()
    eng = engine.Engine(uinput=ui)
    eng.set_bindings({"KEY_F13": "m"})
    eng.handle_event("KEY_F13", 1)
    assert (ecodes.EV_KEY, ecodes.KEY_M, 1) in ui.events
    assert ui.synced >= 1


def test_mapped_button_up_releases_key():
    from evdev import ecodes
    ui = FakeUInput()
    eng = engine.Engine(uinput=ui)
    eng.set_bindings({"KEY_F13": "m"})
    eng.handle_event("KEY_F13", 0)
    assert (ecodes.EV_KEY, ecodes.KEY_M, 0) in ui.events


def test_unmapped_button_injects_nothing():
    ui = FakeUInput()
    eng = engine.Engine(uinput=ui)
    eng.set_bindings({"KEY_F13": "m"})
    eng.handle_event("KEY_F14", 1)
    assert ui.events == []


def test_autorepeat_value_ignored():
    ui = FakeUInput()
    eng = engine.Engine(uinput=ui)
    eng.set_bindings({"KEY_F13": "m"})
    eng.handle_event("KEY_F13", 2)
    assert ui.events == []
