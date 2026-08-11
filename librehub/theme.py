"""GTK CSS theming for LibreHub.

Dark/light is driven by GTK's own theme (``gtk-application-prefer-dark-theme``)
so that *every* surface — including popovers, dialogs and combo dropdowns,
which are separate top-level windows — stays consistent, and hover/active
states come from the system theme. Our provider only adds the brand accent
and component shapes, built from the theme's own color variables
(``@theme_base_color`` etc.) so they adapt to whatever theme is active
instead of hardcoding light values that fight a dark desktop.
"""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402

CSS = b"""
@define-color accent #17916b;

/* surfaces built from the active theme's own colors ---------------------- */
.lh-root { background: @theme_base_color; color: @theme_fg_color; }

.lh-title { font-weight: 700; }

/* status pill */
.status-pill { background: mix(@theme_base_color, @accent, 0.16);
               border: none; border-radius: 999px; padding: 1px 8px 1px 7px; }
.status-pill label { color: @accent; font-size: 11px; font-weight: 700; }
.status-dot { min-width: 6px; min-height: 6px; border-radius: 999px;
              background: @accent; margin-right: 5px; }
.status-pill.paused { background: mix(@theme_base_color, @warning_color, 0.16); }
.status-pill.paused label { color: @warning_color; }
.status-pill.paused .status-dot { background: @warning_color; }

/* buttons: primary is fully branded; secondary/icon inherit the theme's
   background + hover (that is what keeps hover consistent) and we only set
   shape. */
button.lh-primary { background: @accent; color: #ffffff; border: none;
                    border-radius: 6px; padding: 7px 13px; font-weight: 700; }
button.lh-primary:hover { background: shade(@accent, 0.94); }
button.lh-primary:active { background: shade(@accent, 0.86); }
button.lh-secondary { border-radius: 6px; padding: 6px 12px; }
button.lh-icon, button.lh-overflow { border-radius: 6px; padding: 4px;
                                     min-width: 30px; min-height: 30px; }
button.add-game { border-radius: 6px; padding: 8px; font-weight: 700; }

/* sidebar */
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
.appid, .count { color: alpha(@theme_fg_color, 0.5); font-size: 11.5px; }
list.profile-list row:selected .appid,
list.profile-list row:selected .count { color: alpha(#ffffff, 0.85); }
.avatar.editing { background: @accent; color: #ffffff; }
.sidebar-footer { border-top: 1px solid @borders; padding: 10px; }

/* content pane */
.title-block { padding: 20px 24px 14px 24px; border-bottom: 1px solid @borders; }
.game-title { font-size: 21px; font-weight: 700; }
.subtitle { color: alpha(@theme_fg_color, 0.6); font-size: 13px; }

/* bindings list */
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

/* footer strip */
.footer-bar { border-top: 1px solid @borders; padding: 10px 24px; }
.footer-bar label { color: alpha(@theme_fg_color, 0.6); font-size: 12.5px; }

/* empty state */
.empty-title { font-size: 18px; font-weight: 700; }
.empty-body { color: alpha(@theme_fg_color, 0.6); font-size: 14px; }

/* error banner */
.banner { background: mix(@theme_base_color, @warning_color, 0.13);
          border: 1px solid alpha(@warning_color, 0.5); border-radius: 8px;
          padding: 13px 14px; }
.banner-glyph { color: @warning_color; font-weight: 700; }
.banner-title { font-weight: 700; font-size: 14px; }
.banner-body { color: alpha(@theme_fg_color, 0.7); font-size: 13px; }

/* popover menu items */
.lh-popover { padding: 5px; }
button.popover-item { background: none; border: none; border-radius: 5px;
                      padding: 8px 10px; font-size: 13.5px; }
button.popover-item:hover { background: alpha(@theme_fg_color, 0.08); }
button.popover-item.destructive { color: @error_color; }
button.popover-item.destructive:hover { background: alpha(@error_color, 0.14); }

/* inline rename */
list.profile-list row.editing { background: mix(@theme_base_color, @accent, 0.14); }

/* cards / dialogs / wizard */
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


def install() -> None:
    """Install the CSS provider on the default screen (idempotent)."""
    global _provider
    if _provider is not None:
        return
    _provider = Gtk.CssProvider()
    _provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), _provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def apply_appearance(appearance: str) -> None:
    """Set the whole app's light/dark via the GTK theme.

    'system' restores whatever the desktop configured; 'light'/'dark' force
    the theme's variant. Because this flips the *theme*, popovers, dialogs and
    hover states all follow — no per-widget class juggling.
    """
    global _orig_prefer_dark
    settings = Gtk.Settings.get_default()
    if settings is None:
        return
    if _orig_prefer_dark is None:
        _orig_prefer_dark = settings.get_property(
            "gtk-application-prefer-dark-theme")
    if appearance == "dark":
        settings.set_property("gtk-application-prefer-dark-theme", True)
    elif appearance == "light":
        settings.set_property("gtk-application-prefer-dark-theme", False)
    else:  # system
        settings.set_property("gtk-application-prefer-dark-theme",
                              _orig_prefer_dark)
