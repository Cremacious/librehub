"""Layer 2: translate grabbed signal keys into injected keystrokes."""
from __future__ import annotations

from evdev import InputDevice, UInput, ecodes, list_devices

from . import keys, selection


def find_signal_device(model: str) -> str | None:
    """Path of the mouse's keyboard endpoint (name matches model, has KEY_F13)."""
    f13 = ecodes.KEY_F13
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except OSError:
            continue
        caps = dev.capabilities().get(ecodes.EV_KEY, [])
        if model.lower() in dev.name.lower() and f13 in caps:
            return path
    return None


class Engine:
    def __init__(self, uinput=None):
        self._ui = uinput if uinput is not None else UInput()
        self._bindings: dict[str, str] = {}

    def set_bindings(self, bindings: dict[str, str]) -> None:
        self._bindings = dict(bindings)

    def handle_event(self, code_name: str, value: int) -> None:
        if value not in (0, 1):  # ignore autorepeat (2)
            return
        out = selection.resolve_output(self._bindings, code_name)
        if out is None:
            return
        try:
            code = keys.to_code(out)
        except ValueError:
            return
        self._ui.write(ecodes.EV_KEY, code, value)
        self._ui.syn()

    async def run(self, device_path: str, on_detect=None) -> None:
        dev = InputDevice(device_path)
        dev.grab()
        try:
            async for event in dev.async_read_loop():
                if event.type != ecodes.EV_KEY:
                    continue
                name = ecodes.KEY.get(event.code)
                if name is None:
                    continue
                if on_detect is not None and event.value == 1 and on_detect(name):
                    continue  # consumed by detect mode
                self.handle_event(name, event.value)
        finally:
            dev.ungrab()
