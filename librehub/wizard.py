"""First-run setup wizard — one decision per step, replacing the old
health-check dialog's wall of text. Four steps: permissions → daemon →
pick buttons → done. See design_handoff_librehub_ui/README.md screens 5–6.
"""
from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from . import config as C  # noqa: E402
from . import preflight, prefs as P, theme  # noqa: E402

_STEPS = 4


class Wizard(Gtk.Window):
    def __init__(self, prefs: P.Prefs):
        super().__init__(title="Set up LibreHub")
        self.prefs = prefs
        self.step = 1
        self.get_style_context().add_class("lh-root")
        theme.apply_appearance(prefs.appearance)
        self.set_resizable(False)
        self.set_default_size(640, 460)
        self.set_size_request(640, 460)

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.get_style_context().add_class("lh-header")
        title = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        t = Gtk.Label(label="Set up LibreHub")
        t.get_style_context().add_class("lh-title")
        title.pack_start(t, False, False, 0)
        self.counter = Gtk.Label()
        self.counter.get_style_context().add_class("step-counter")
        title.pack_end(self.counter, False, False, 0)
        title.show_all()
        hb.set_custom_title(title)
        self.set_titlebar(hb)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(root)

        prog = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        prog.set_margin_top(20)
        prog.set_margin_start(34)
        prog.set_margin_end(34)
        prog.set_margin_bottom(26)
        self.segs = []
        for _ in range(_STEPS):
            s = Gtk.Box()
            s.get_style_context().add_class("progress-seg")
            s.set_size_request(-1, 4)
            prog.pack_start(s, True, True, 0)
            self.segs.append(s)
        root.pack_start(prog, False, False, 0)

        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.body.set_margin_start(34)
        self.body.set_margin_end(34)
        root.pack_start(self.body, True, True, 0)

        self.action = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.action.get_style_context().add_class("action-bar")
        root.pack_end(self.action, False, False, 0)

        self._render()

    # ------------------------------------------------------------------
    def _clear(self, box):
        for ch in box.get_children():
            box.remove(ch)

    def _title(self, text):
        lbl = Gtk.Label(label=text, xalign=0)
        lbl.get_style_context().add_class("wizard-title")
        lbl.set_margin_bottom(10)
        return lbl

    def _body_text(self, text):
        lbl = Gtk.Label(label=text, xalign=0)
        lbl.get_style_context().add_class("wizard-body")
        lbl.set_line_wrap(True)
        lbl.set_max_width_chars(52)
        return lbl

    def _checklist(self, checks):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        card.get_style_context().add_class("wizard-card")
        card.set_margin_top(22)
        for chk in checks:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            ok = chk.status is preflight.Status.OK
            mark = Gtk.Label(label="✓" if ok else "•")
            mark.get_style_context().add_class("check-ok" if ok
                                               else "check-missing")
            row.pack_start(mark, False, False, 0)
            row.pack_start(Gtk.Label(label=chk.detail, xalign=0),
                           True, True, 0)
            card.pack_start(row, False, False, 0)
        return card

    def _btn(self, label, primary=False):
        b = Gtk.Button(label=label)
        b.get_style_context().add_class("lh-primary" if primary
                                        else "lh-secondary")
        return b

    def _busy(self, button, msg):
        button.set_sensitive(False)
        button.set_label(msg)

    # ------------------------------------------------------------------
    def _render(self):
        self.counter.set_text(f"Step {self.step} of {_STEPS}")
        for i, s in enumerate(self.segs):
            ctx = s.get_style_context()
            if i < self.step:
                ctx.add_class("done")
            else:
                ctx.remove_class("done")
        self._clear(self.body)
        self._clear(self.action)
        {1: self._step_permissions, 2: self._step_daemon,
         3: self._step_buttons, 4: self._step_done}[self.step]()
        self.body.show_all()
        self.action.show_all()

    def _advance(self):
        if self.step < _STEPS:
            self.step += 1
            self._render()

    def _back(self):
        if self.step > 1:
            self.step -= 1
            self._render()

    # step 1 -----------------------------------------------------------
    def _step_permissions(self):
        self.body.pack_start(self._title("Give LibreHub permission"),
                             False, False, 0)
        self.body.pack_start(self._body_text(
            "One password prompt installs the missing system packages, the "
            "udev rule for the virtual keyboard, and adds you to the input "
            "group."), False, False, 0)
        checks = [c for c in preflight.run_all()
                  if c.key in ("packages", "uinput", "input_group")]
        self.body.pack_start(self._checklist(checks), False, False, 0)

        hint = Gtk.Label(label="You can quit and finish later", xalign=0)
        hint.get_style_context().add_class("hint")
        self.action.pack_start(hint, True, True, 0)
        skip = self._btn("Skip")
        skip.connect("clicked", lambda _b: self._advance())
        cont = self._btn("Continue", primary=True)

        def go(_b):
            self._busy(cont, "Working…")

            def work():
                ok, msg = preflight.run_privileged_setup()
                GLib.idle_add(lambda: (self._render(), None)[1])
            threading.Thread(target=work, daemon=True).start()
        cont.connect("clicked", go)
        self.action.pack_end(cont, False, False, 0)
        self.action.pack_end(skip, False, False, 0)

    # step 2 -----------------------------------------------------------
    def _step_daemon(self):
        self.body.pack_start(self._title("Start the background service"),
                             False, False, 0)
        self.body.pack_start(self._body_text(
            "The daemon watches which game is focused and does the actual "
            "button-to-key remapping."), False, False, 0)
        checks = [c for c in preflight.run_all() if c.key == "daemon"]
        self.body.pack_start(self._checklist(checks), False, False, 0)

        back = self._btn("Back")
        back.connect("clicked", lambda _b: self._back())
        self.action.pack_start(back, False, False, 0)
        cont = self._btn("Continue", primary=True)

        def go(_b):
            self._busy(cont, "Starting…")

            def work():
                preflight.start_daemon()
                GLib.idle_add(lambda: (self._advance(), None)[1])
            threading.Thread(target=work, daemon=True).start()
        cont.connect("clicked", go)
        self.action.pack_end(cont, False, False, 0)

    # step 3 -----------------------------------------------------------
    def _step_buttons(self):
        self.body.pack_start(self._title("Pick the buttons to manage"),
                             False, False, 0)
        self.body.pack_start(self._body_text(
            "Assign each mouse button you want to remap a hidden signal. "
            "Left, right and middle click stay untouched."), False, False, 0)
        choose = self._btn("Choose buttons…")
        choose.set_halign(Gtk.Align.START)
        choose.set_margin_top(22)

        def open_setup(_b):
            from . import gui
            gui.show_setup_mouse(self)
        choose.connect("clicked", open_setup)
        self.body.pack_start(choose, False, False, 0)

        back = self._btn("Back")
        back.connect("clicked", lambda _b: self._back())
        self.action.pack_start(back, False, False, 0)
        cont = self._btn("Continue", primary=True)
        cont.connect("clicked", lambda _b: self._advance())
        self.action.pack_end(cont, False, False, 0)

    # step 4 -----------------------------------------------------------
    def _step_done(self):
        self.body.pack_start(self._title("You're all set"), False, False, 0)
        self.body.pack_start(self._body_text(
            "Add a game from the sidebar, then bind its buttons. LibreHub "
            "switches profiles automatically when a game is focused."),
            False, False, 0)
        back = self._btn("Back")
        back.connect("clicked", lambda _b: self._back())
        self.action.pack_start(back, False, False, 0)
        finish = self._btn("Finish", primary=True)
        finish.connect("clicked", lambda _b: self._finish())
        self.action.pack_end(finish, False, False, 0)

    def _finish(self):
        # Mark first-run done by ensuring a config file exists.
        if not C.config_path().exists():
            try:
                C.save(C.default_config(), C.config_path())
            except OSError:
                pass
        self.destroy()


def run_first_run(prefs: P.Prefs) -> None:
    """Show the wizard and block until it closes (its own main loop)."""
    theme.install()
    w = Wizard(prefs)
    w.connect("destroy", Gtk.main_quit)
    w.show_all()
    w.present()
    Gtk.main()
