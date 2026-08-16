from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

ICON_NAME = "librehub"

APP_ID = "librehub"
WM_CLASS = "LibreHub"

CSS = b"""
@define-color accent #17916b;

.lh-root { background: @theme_base_color; color: @theme_fg_color; }

.lh-title { font-weight: 700; }

.status-pill { background: mix(@theme_base_color, @accent, 0.16);
               border: none; border-radius: 999px; padding: 1px 8px 1px 7px; }
.status-pill label { color: @accent; font-size: 11px; font-weight: 700; }
.status-dot { min-width: 6px; min-height: 6px; border-radius: 999px;
              background: @accent; margin-right: 5px; }
.status-pill.paused { background: mix(@theme_base_color, @warning_color, 0.16); }
.status-pill.paused label { color: @warning_color; }
.status-pill.paused .status-dot { background: @warning_color; }

button.lh-primary { background: @accent; color: #ffffff; border: none;
                    border-radius: 6px; padding: 7px 13px; font-weight: 700; }
button.lh-primary:hover { background: shade(@accent, 0.94); }
button.lh-primary:active { background: shade(@accent, 0.86); }
button.lh-secondary { border-radius: 6px; padding: 6px 12px; }
button.lh-icon, button.lh-overflow { border-radius: 6px; padding: 4px;
                                     min-width: 30px; min-height: 30px; }
button.lh-overflow { background-color: transparent; background-image: none;
                     border: none; box-shadow: none;
                     color: alpha(@theme_fg_color, 0.55); }
button.lh-overflow:hover { background-color: alpha(@theme_fg_color, 0.12); }
list.profile-list row:selected button.lh-overflow { color: #ffffff; }
list.profile-list row:selected button.lh-overflow:hover {
    background-color: alpha(#ffffff, 0.22); }
button.add-game { border-radius: 6px; padding: 8px; font-weight: 700; }

.lh-sidebar { background: @theme_bg_color; border-right: 1px solid @borders; }
.section-header { color: alpha(@theme_fg_color, 0.5); font-size: 11.5px;
                 font-weight: 700; padding: 14px 14px 8px 14px; }
list.profile-list { background: transparent; }
list.profile-list row { border-radius: 6px; margin: 1px 6px; }
list.profile-list row:hover { background: alpha(@theme_fg_color, 0.06); }
list.profile-list row:selected,
list.profile-list row:selected:hover { background: @accent; }
list.profile-list row:selected label { color: #ffffff; }
.avatar { background: alpha(@theme_fg_color, 0.10);
          color: alpha(@theme_fg_color, 0.65); border-radius: 5px;
          min-width: 22px; min-height: 22px; font-weight: 700; font-size: 12px; }
list.profile-list row:selected .avatar { background: alpha(#ffffff, 0.22);
                                         color: #ffffff; }
.appid { color: alpha(@theme_fg_color, 0.5); font-size: 11.5px; }
list.profile-list row:selected .appid { color: alpha(#ffffff, 0.85); }
.avatar.editing { background: @accent; color: #ffffff; }
.sidebar-footer { border-top: 1px solid @borders; padding: 10px; }

.title-block { padding: 20px 24px 14px 24px; border-bottom: 1px solid @borders; }
.game-title { font-size: 21px; font-weight: 700; }
.subtitle { color: alpha(@theme_fg_color, 0.6); font-size: 13px; }

list.bindings { background: transparent; }
list.bindings row + row { border-top: 1px solid alpha(@theme_fg_color, 0.08); }
.chip { background: alpha(@theme_fg_color, 0.06); border: 1px solid @borders;
        border-radius: 6px; padding: 5px 10px; font-size: 13px; min-width: 118px; }
.arrow { color: alpha(@theme_fg_color, 0.35); }
.keycap { background: @theme_base_color; border: 1px solid @borders;
          border-radius: 6px; padding: 6px 12px; font-family: monospace;
          font-size: 13px; min-width: 62px; box-shadow: 0 1.5px 0 @borders; }
.keycode { color: alpha(@theme_fg_color, 0.45); font-size: 12.5px;
           font-family: monospace; }
button.remove { background: none; border: none; padding: 4px;
                min-width: 28px; min-height: 28px; }
button.remove:hover { background: alpha(@theme_fg_color, 0.09);
                      border-radius: 6px; }

.footer-bar { border-top: 1px solid @borders; padding: 10px 24px; }
.footer-bar label { color: alpha(@theme_fg_color, 0.6); font-size: 12.5px; }

.empty-title { font-size: 18px; font-weight: 700; }
.empty-body { color: alpha(@theme_fg_color, 0.6); font-size: 14px; }

.banner { background: mix(@theme_base_color, @warning_color, 0.13);
          border: 1px solid alpha(@warning_color, 0.5); border-radius: 8px;
          padding: 13px 14px; }
.banner-glyph { color: @warning_color; font-weight: 700; }
.banner-title { font-weight: 700; font-size: 14px; }
.banner-body { color: alpha(@theme_fg_color, 0.7); font-size: 13px; }

.lh-popover { padding: 5px; }
button.popover-item { background: none; border: none; border-radius: 5px;
                      padding: 8px 10px; font-size: 13.5px; }
button.popover-item:hover { background: alpha(@theme_fg_color, 0.08); }
button.popover-item.destructive { color: @error_color; }
button.popover-item.destructive:hover { background: alpha(@error_color, 0.14); }

list.profile-list row.editing { background: mix(@theme_base_color, @accent, 0.14); }

.card { border: 1px solid @borders; border-radius: 8px;
        background: @theme_base_color; }
.card row + row { border-top: 1px solid @borders; }
.dialog-headline { font-size: 19px; font-weight: 700; }
.dialog-body { color: alpha(@theme_fg_color, 0.6); font-size: 14px; }
.pending-slot { border: 2px dashed @accent; border-radius: 6px; color: @accent;
                font-family: monospace; font-size: 13px; padding: 8px 14px;
                min-width: 54px; }
.wait-circle { background: mix(@theme_base_color, @accent, 0.16);
               border-radius: 999px; min-width: 54px; min-height: 54px;
               color: @accent; font-size: 22px; }
entry.lh-entry { border-radius: 6px; padding: 8px 10px; }

.progress-seg { min-height: 4px; border-radius: 2px;
                background: alpha(@theme_fg_color, 0.15); }
.progress-seg.done { background: @accent; }
.wizard-title { font-size: 24px; font-weight: 700; }
.wizard-body { color: alpha(@theme_fg_color, 0.65); font-size: 15px; }
.wizard-card { background: alpha(@theme_fg_color, 0.03);
               border: 1px solid @borders; border-radius: 8px; padding: 14px 16px; }
.check-ok { color: @accent; }
.check-missing { color: @warning_color; }
.action-bar { border-top: 1px solid @borders; padding: 12px 20px; }
.step-counter { color: alpha(@theme_fg_color, 0.6); font-size: 12.5px; }
.hint { color: alpha(@theme_fg_color, 0.5); font-size: 13px; }
.confirm-strip { background: @theme_bg_color; border: 1px solid @borders;
                 border-radius: 6px; padding: 9px 12px; }
.mono { font-family: monospace; }
"""

_provider: Gtk.CssProvider | None = None
_orig_prefer_dark: bool | None = None
_orig_theme_name: str | None = None
_probe: "Gtk.Box | None" = None

FALLBACK_THEME = "Adwaita"


def claim_identity() -> None:
    GLib.set_prgname(APP_ID)
    Gdk.set_program_class(WM_CLASS)
    Gtk.Window.set_default_icon_name(ICON_NAME)


def is_light_color(red: float, green: float, blue: float) -> bool:
    return 0.299 * red + 0.587 * green + 0.114 * blue > 0.5


def install() -> None:
    claim_identity()
    global _provider
    if _provider is not None:
        return
    _provider = Gtk.CssProvider()
    _provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), _provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def _background_is_light() -> bool | None:
    global _probe
    if _probe is None:
        _probe = Gtk.Box()
    found, color = _probe.get_style_context().lookup_color("theme_base_color")
    if not found:
        return None
    return is_light_color(color.red, color.green, color.blue)


def apply_appearance(appearance: str) -> None:
    global _orig_prefer_dark, _orig_theme_name
    settings = Gtk.Settings.get_default()
    if settings is None:
        return
    if _orig_prefer_dark is None:
        _orig_prefer_dark = settings.get_property(
            "gtk-application-prefer-dark-theme")
        _orig_theme_name = settings.get_property("gtk-theme-name")

    if appearance not in ("light", "dark"):
        settings.set_property("gtk-theme-name", _orig_theme_name)
        settings.set_property("gtk-application-prefer-dark-theme",
                              _orig_prefer_dark)
        return

    want_light = appearance == "light"
    settings.set_property("gtk-theme-name", _orig_theme_name)
    settings.set_property("gtk-application-prefer-dark-theme", not want_light)
    if _background_is_light() is want_light:
        return
    settings.set_property("gtk-theme-name", FALLBACK_THEME)
    settings.set_property("gtk-application-prefer-dark-theme", not want_light)
