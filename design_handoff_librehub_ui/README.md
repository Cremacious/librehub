# Handoff: LibreHub UI redesign

## Overview

LibreHub is a per-game mouse-button remapper for Linux (the open answer to Logitech G HUB's per-game feature). It ships a GTK3 editor (`librehub/gui.py`) plus a daemon; the editor lets a user pick a game profile and map mouse buttons to keyboard keys.

This handoff covers a redesign of that editor's entire UI. The goals came from the user directly:

- **Fixed, consistent window sizes.** The current app opens windows at whatever size each dialog happens to request; the redesign pins one size per window class.
- **Less thrown at the user at once.** The current sidebar stacks six buttons under the game list and the health-check dialog dumps five paragraphs of remediation text. The redesign reduces each pane to one primary action plus a per-row overflow menu, and turns first-run remediation into a stepped assistant.
- **Both light and dark themes.**
- **Same two-pane model** (games left, bindings right) — the structure was not the problem.
- **Stay buildable in plain GTK3.** No custom drawing, no GTK4-only widgets, no external toolkit. Every element in these mocks maps to a stock GTK3 widget (see "GTK3 widget mapping" below).

## About the design files

The files in this bundle are **design references created in HTML**. They are prototypes showing the intended look, layout, and behavior — not production code to copy. `LibreHub Redesign.dc.html` is a static canvas of window mocks laid out side by side; it is not an interactive prototype and has no JavaScript logic.

The implementation task is to **recreate these designs in the existing codebase's environment**: Python 3 + GTK3 via PyGObject, in `librehub/gui.py` (and new sibling modules as needed), styled with a GTK CSS provider. Do not introduce a web view, Electron, or a different toolkit.

`LibreHub Current UI.dc.html` is a faithful recreation of the *existing* GTK3 UI, rendered with Adwaita-like default styling. It exists as a before/after reference so you can see what each change replaces.

## Fidelity

**High-fidelity.** Colors, type sizes, spacing, radii, and copy are final and exact. Recreate the UI to match, using GTK3 widgets plus a CSS provider for the color/spacing values.

Two caveats on what "pixel-perfect" means for a GTK app:

- The **window title bar / header bar** in the mocks (including the –, □, ✕ buttons) is drawn to show intent. In the real app it is a `Gtk.HeaderBar` with `show_close_button=True`; the window controls come from the user's Cinnamon theme and should not be styled.
- **Font** in the mocks is Cantarell at browser pixel sizes. In GTK, do not hardcode a font family — inherit the system UI font. Where the mocks use a size other than the default body size, express it as the ratio given in the type scale below.

## Design tokens

### Colors — light

| Token | Hex | Used for |
|---|---|---|
| Accent | `#17916b` | Primary buttons, selected sidebar row, status dot, progress fill, focus ring |
| Accent pressed / text-on-light | `#0f6e50` | Status pill text, link hover |
| Accent tint | `#e8f4ef` | Status pill background, avatar tint, inline-edit row background |
| Accent tint border | `#b6e0cf` | Text-selection highlight in inline edit |
| Window background | `#ffffff` | Content pane |
| Sidebar background | `#f7f6f5` | Left pane, footer strips |
| Header bar background | `linear-gradient(#fdfdfc, #f3f2f0)` | `Gtk.HeaderBar` |
| Raised control background | `#ffffff` | Secondary buttons, entries, key caps |
| Sunken/inert fill | `#f2f1f0` | Button-name chips, segmented-control track |
| Border strong | `#cfcac6` | Window border, entry border, key-cap border |
| Border medium | `#d6d1cd` | Secondary button border |
| Border light | `#e4e0dc` | Pane dividers, card borders |
| Border hairline | `#eeebe8` | Section rules, list-row separators inside cards |
| Row separator | `#f1efec` | Binding-list row separators |
| Text primary | `#1d2022` | Titles, values |
| Text secondary | `#55605c` | Body copy |
| Text tertiary | `#6f7679` | Subtitles, footer text, dialog step counter |
| Text quaternary | `#8a908d` | Section headers, hints |
| Text disabled/meta | `#9aa09d` | Raw keycodes, AppIDs in lists |
| Placeholder text | `#9a9996` | Entry placeholders |
| Glyph muted | `#b6bbb8` | The `→` arrow between button and key |
| Destructive | `#b3261e` | "Remove game" menu item |
| Warning fill | `#fdf4e7` | Error/paused banner background |
| Warning border | `#ecd7b0` | Error banner border |
| Warning text/glyph | `#a9741a` | Error banner `!` glyph |
| Warning bullet (wizard) | `#b58a24` | "missing" bullets in the wizard checklist |
| Card background subtle | `#faf9f8` | Wizard checklist card |
| Toggle off track | `#dcd8d4` | Off `Gtk.Switch` |

### Colors — dark

| Token | Hex | Used for |
|---|---|---|
| Accent | `#17916b` | Same role as light (unchanged) |
| Accent text on dark | `#58d3a3` | Status pill text |
| Accent dot | `#2fbe8d` | Status pill dot |
| Accent tint | `#22352d` | Status pill background |
| Window background | `#242628` | Content pane |
| Sidebar background | `#1f2123` | Left pane |
| Header bar background | `#1c1e20` | `Gtk.HeaderBar` |
| Window border | `#121415` | Outer border, header bar bottom border |
| Raised control background | `#2b2e31` | Secondary buttons, chips, sidebar avatars |
| Key cap background | `#32363a` | Key caps |
| Key cap border | `#43484c` | Key caps |
| Key cap shadow | `#1a1c1e` | 1.5px bottom shadow on key caps |
| Border medium | `#3a3e41` | Secondary button border |
| Border light | `#35383b` | Card borders, wizard list borders |
| Pane divider | `#2f3234` | Sidebar/content divider, section rules |
| Row separator | `#2b2e30` | Binding-list row separators |
| Text primary | `#eceff1` | Titles, values |
| Text secondary | `#b3b9bd` | Wizard body copy |
| Text tertiary | `#9aa0a4` | Subtitles, footer, window control glyphs |
| Text quaternary | `#7d8388` | Section headers, keycodes, AppIDs |
| Glyph muted | `#5c6265` | The `→` arrow |
| Toggle off track | `#43484c` | Off `Gtk.Switch` |
| Toggle off knob | `#9aa0a4` | Off `Gtk.Switch` knob |
| Divider muted | `#4a4f52` | Footer `·` separators |

### Type scale

Base body size in the mocks is **14.7px** (GTK's default at the user's DPI). Express everything else relative to it.

| Role | Size | Weight | Notes |
|---|---|---|---|
| Window/dialog title (header bar) | 14.7px | 700 | |
| Content pane title (game name) | 21px | 700 | |
| Wizard step title | 24px | 700 | |
| Dialog headline | 19px | 700 | Add-binding steps |
| Empty-state headline | 18px | 700 | |
| Wizard body copy | 15px | 400 | line-height 1.5 |
| Body / list rows | 14.7px | 400 | |
| Dialog body copy | 14px | 400 | line-height 1.5 |
| Secondary button label | 13.5px | 400 (700 when primary) | |
| Subtitle under title | 13px | 400 | |
| Chips, key caps, small meta | 13px | 400 | |
| Footer bar, step counter, pill | 12.5px | 400 (700 for pill) | |
| AppID under sidebar name | 11.5px | 400 | |
| Section header ("PROFILES") | 11.5px | 700 | uppercase, letter-spacing `.1em` |

Monospace (`DejaVu Sans Mono`) is used only for key caps, raw keycodes, and the literal `input` group name.

### Spacing, radius, elevation

- Spacing steps used: 2, 4, 6, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 32, 34, 42, 46 px. Keep to these.
- Radius: `999px` pill (status pill, switch), `8px` cards and popovers, `10px 10px 5px 5px` window frames, `7px` segmented-control track, `6px` buttons/entries/chips/key caps, `5px` menu items and small avatars/badges, `4px` inline-edit entry, `2px` progress segments.
- Elevation (mock-only; the real windows get shadows from the compositor): main window `0 18px 46px rgba(0,0,0,.3)` light / `.45` dark; medium dialogs `0 14px 36px`; small dialogs `0 12px 30px`; popover `0 10px 26px rgba(0,0,0,.22)`.
- Key caps carry a `0 1.5px 0` bottom shadow in the border color to read as physical keys.
- Progress segments in the wizard are 4px tall, `gap: 6px`, equal flex.

### Window sizes (fixed — this is the core fix)

| Window | Size | Resizable |
|---|---|---|
| Main window | 900 × 600 (header bar 46, content 553) | Yes, with 900×600 as the default and minimum |
| First-run wizard | 640 × 460 (header bar 46, content 413) | No |
| All dialogs (add binding ×2, add game, preferences, confirmations) | 480 wide, height to content; header bar 44 | No |

Every dialog is 480 wide. Do not let content set dialog width.

## Screens / views

### 1. Main window — light (mock `1a`, `data-screen-label="Main window light"`)

**Purpose:** pick a profile, see and edit its bindings, read remap status at a glance.

**Layout:** `Gtk.HeaderBar` (46px) over a horizontal split: 250px sidebar, 1px divider (`#e4e0dc`), content pane fills the rest.

**Header bar**, left to right, `gap: 10px`, padding `0 8px 0 14px`:
- Title "LibreHub", 700.
- **Status pill**, `margin-left: 6px`, padding `3px 9px 3px 7px`, radius `999px`, background `#e8f4ef`, text `#0f6e50` 12.5px/700, with a 7px `#17916b` dot and 7px gap. Copy: "Remapping active".
- Spacer, then a 30×30 hamburger button (`≡`), radius 6, border `#d6d1cd`, background white, glyph `#55605c` 15px. This is the app menu (Preferences, Health check, About).

**Sidebar** (`#f7f6f5`), vertical:
- Section header "PROFILES": padding `14px 14px 8px`, 11.5px/700, uppercase, `letter-spacing .1em`, `#8a908d`.
- Rows, container padding `0 6px`, each row `display: flex; gap: 10px; padding: 9px 10px; border-radius: 6px`:
  - 22×22 avatar, radius 5, `#e6e3e0` background, `#6f7679` glyph 12px — the game's initial, or `★` for Default.
  - Name (14.7px). For games, a second line with the AppID at 11.5px `#8a908d`.
  - Trailing: binding count, 12px `#8a908d`.
  - **Selected row:** background `#17916b`, text white; avatar background `rgba(255,255,255,.22)`; AppID at `opacity .8`; the trailing count is replaced by a 22×22 `⋯` overflow button with `rgba(255,255,255,.2)` background, radius 5.
  - Rows shown: Default (★, count 2), Deep Rock Galactic / 548430 (selected), Helldivers 2 / 553850 (count 4), Grand Theft Auto V / 271590 (count 2).
- Footer, pushed to the bottom, `border-top: 1px solid #e4e0dc`, padding 10: one full-width secondary button "+ Add game", padding 8, radius 6, border `#d6d1cd`, white, 13.5px/700.

That footer button is the whole point of the sidebar change: the current UI's five stacked buttons ("Add game I'm playing now", "Add by AppID…", "Remove selected game", "Rename selected game", "Set up mouse", "Setup / Health check") become **one** button plus the per-row `⋯` menu plus the header-bar app menu.

**Content pane:**
- Title block, padding `20px 24px 14px`, `border-bottom: 1px solid #eeebe8`: game name 21px/700; subtitle 13px `#6f7679` — "3 buttons bound · switches on automatically when this game is focused". Right-aligned: primary button "Add binding" (padding `7px 13px`, radius 6, `#17916b`, white, 13.5px/700) and a 32×32 `⋯` overflow button (radius 6, border `#d6d1cd`, white).
- Bindings list, padding `8px 16px`. Each row `display: flex; gap: 12px; padding: 12px 8px`, separated by `1px solid #f1efec` (no separator after the last):
  - **Button-name chip**, `min-width: 118px`, padding `5px 10px`, radius 6, background `#f2f1f0`, border `#e2dedb`, 13px, centered. Human names — "Thumb front", "Thumb rear", "Side scroll" — not `KEY_F13`.
  - `→` glyph in `#b6bbb8`.
  - **Key cap**, `min-width: 62px`, padding `6px 12px`, radius 6, white, border `#cfcac6`, `box-shadow: 0 1.5px 0 #cfcac6`, monospace 13px, centered: "M", "Space", "4".
  - Flexible cell with the raw keycode, 12.5px `#9aa09d`: `KEY_F13`, `KEY_F14`, `KEY_F15`.
  - 28×28 `✕` remove button, radius 6, glyph `#9aa09d`.
- Footer bar pushed to the bottom: padding `10px 24px`, `border-top: 1px solid #eeebe8`, 12.5px `#6f7679`, items with `gap: 10px` and `·` separators in `#d3d7d5` — "Logitech G502 HERO", "X11 · per-window switching", and right-aligned "Saved automatically".

The keycode column is what makes this honest: the chip shows the human name, the small grey text still shows the `KEY_F13` the daemon actually uses, so power users can debug.

### 2. Main window — dark (mock `1c`, `data-screen-label="Main window dark"`)

Identical geometry and copy; dark tokens substituted per the table above. The selected sidebar row keeps `#17916b` (accent does not change between themes). Status pill becomes `#22352d` / `#58d3a3` / dot `#2fbe8d`. This mock shows the profile after rename, titled "DRG co-op night", to demonstrate that the AppID subtitle keeps it identifiable.

### 3. Rename — popover (mock `1b`, `data-screen-label="Rename popover"`)

The user added `_on_rename_game` to `gui.py` as a sixth sidebar button plus a modal entry dialog. The redesign keeps the capability and drops both the button and the modal.

**Purpose:** show where rename/duplicate/remove live now.

**Layout:** 560-wide reference frame, header bar 44 with title "Profile menu" and right-aligned hint "right-click a row, or the ⋯ button"; below it a 240-tall two-pane excerpt.

**Popover** — a `Gtk.Popover` anchored to the selected row (`left: 44px; top: 92px` in the mock), 198 wide, white, border `#cfcac6`, radius 8, shadow `0 10px 26px rgba(0,0,0,.22)`, padding 5. Items are 13.5px, padding `8px 10px`, radius 5:
1. "Rename…" — shown hovered (`#f2f1f0`)
2. "Duplicate bindings to…"
3. 1px `#eeebe8` separator with `4px 6px` margin
4. "Remove game" in `#b3261e`

Right pane carries the rationale copy (18px/700 title + 13px `#6f7679` body).

**Behavior:** the popover opens from the row's `⋯` button *and* from right-click / Menu key on the row. "Rename…" starts inline editing (next screen). "Remove game" keeps the existing confirmation, with its current copy: "This deletes its bindings from LibreHub. (It does not change the mouse's onboard button signals.)"

### 4. Rename — inline edit (mock `1b`, `data-screen-label="Rename inline edit"`)

**Purpose:** rename without a modal, without the bindings list disappearing.

**Layout:** same 560 reference frame; header bar title "Renaming", hint "Enter saves · Esc cancels".

**Editing row:** padding drops to `7px 8px`, background `#e8f4ef`, `border: 1px solid #17916b`, radius 6. Avatar becomes solid `#17916b` with white glyph. The name line becomes a `Gtk.Entry`: white, `border: 1px solid #17916b`, radius 4, padding `3px 6px`, 13.5px, pre-filled with the current name, all text selected (selection highlight `#b6e0cf`). The AppID stays visible beneath at 11.5px `#6f7679`.

**Right pane:** title updates live to the typed name ("DRG co-op night"), body copy explains the behavior, and at the bottom a confirmation strip: padding `9px 12px`, radius 6, background `#f7f6f5`, border `#e4e0dc`, 12.5px `#55605c`, with a 6px `#17916b` dot — "Renamed to “DRG co-op night”".

**Behavior:**
- Enter commits; Esc reverts; focus-out commits.
- Empty or whitespace-only input reverts to the previous name (do not write an empty name).
- Committing updates the content-pane title in the same frame — nothing else moves, no dialog appears, no relayout.
- The stored AppID never changes; rename only affects the display name.

If you would rather keep the existing modal code path, the modal still works — but then drop the sidebar button and open the modal from the popover's "Rename…" item, so the sidebar stays at one button.

### 5. First-run wizard, step 1 — permissions (mock `1d`, `data-screen-label="Wizard step 1"`)

**Purpose:** replace the current health-check dialog's wall of remediation text with one decision per step.

**Layout:** 640 × 460, not resizable. Header bar 44–46: title "Set up LibreHub", right-aligned "Step 1 of 4" (12.5px `#6f7679`). Content padding `32px 34px 0`.
- **Progress**: four equal 4px segments, `gap: 6px`, radius 2; completed `#17916b`, pending `#e4e0dc`. `margin-bottom: 26px`.
- Title 24px/700: "Give LibreHub permission". `margin-bottom: 10px`.
- Body 15px `#55605c`, `max-width: 470px`, line-height 1.5: "One password prompt installs the missing system packages, the udev rule for the virtual keyboard, and adds you to the `input` group." (`input` in monospace 13.5px.)
- **Checklist card**, `margin-top: 22px`, padding `14px 16px`, border `#e4e0dc`, radius 8, background `#faf9f8`, `max-width: 470px`, rows `gap: 9px` at 13.5px: `✓` `#17916b` "ratbagd found"; `•` `#b58a24` "python3-evdev missing"; `•` `#b58a24` "udev rule not installed".
- **Action bar** pinned to the bottom, full-bleed (negative 34px side margins), padding `12px 20px`, `border-top: 1px solid #eeebe8`: left hint 13px `#8a908d` "You can quit and finish later"; right, secondary "Skip" then primary "Continue" (padding `8px 18px`, radius 6, `#17916b`, white, 13.5px/700), `gap: 8px`.

**Behavior:** "Continue" triggers the existing single `pkexec` remediation path. The checklist reflects live probe results from `preflight.py` — render it from the real check results, not a fixed list. The four steps are: 1 permissions → 2 daemon → 3 pick buttons → 4 done.

### 6. First-run wizard, step 3 — pick buttons (mock `1d`, `data-screen-label="Wizard step 3"`, dark)

**Purpose:** the current "Set up mouse" dialog, in the flow, with switches instead of check buttons and human names instead of ratbag jargon.

Same frame as step 1, dark tokens, progress at 3/4.
- Title "Pick the buttons to manage".
- Body `#b3b9bd`: "Logitech G502 HERO. Left, right and middle click stay untouched."
- **List card**: `margin-top: 20px`, border `#35383b`, radius 8, `overflow: hidden`; rows padding `12px 14px`, background `#2b2e31`, separated by `1px solid #35383b`. Each row: label + ` · button N` in `#7d8388` 13px, then a `Gtk.Switch` on the right — 40×22 track, radius 999, 2px padding, 18px knob; on = `#17916b` track + white knob, off = `#43484c` track + `#9aa0a4` knob.
- Rows: "Thumb front · button 4" (on), "Thumb rear · button 5" (on), "Sniper button · button 6" (off).
- Action bar: left "2 of 3 selected" 13px `#7d8388`; right "Back" (secondary) + "Continue" (primary).

**Behavior:** the caveat the current UI shows in a message dialog ("unchecking a button here stops LibreHub from managing it, but does not restore its original function…") moves to a small inline note under the list when a switch is turned **off** — show it only then, not preemptively.

### 7. Add binding, step 1 of 2 (mock `1e`, `data-screen-label="Add binding step 1"`)

480 wide, header bar 44 with title "Add binding" and right-aligned "1 of 2". Content padding `34px 28px 0`, centered, `gap: 12px`:
- 54×54 circle, background `#e8f4ef`, glyph `◉` `#17916b` 22px.
- Headline 19px/700: "Press a mouse button".
- Body 14px `#55605c`, `max-width: 330px`: "Any of the buttons you set up. Waiting…".
- Action bar `margin-top: 22px`, `border-top: 1px solid #eeebe8`, padding `12px 20px`, right-aligned secondary "Cancel".

**Behavior:** grabs the device and waits. The circle should pulse gently while waiting (see Interactions).

### 8. Add binding, step 2 of 2 (mock `1e`, `data-screen-label="Add binding step 2"`)

Same frame, "2 of 2". Content padding `30px 28px 0`, centered:
- A preview row, `gap: 12px`: the captured button as a chip (padding `6px 12px`, radius 6, `#f2f1f0`, border `#e2dedb`, 13px, "Thumb front"), the `→` glyph in `#b6bbb8`, then a **pending key slot**: `min-width: 54px`, padding `8px 14px`, radius 6, `border: 2px dashed #17916b`, text `#17916b`, monospace 13px, content `?`.
- Headline 19px/700 (`margin-top: 4px`): "Now press the key it should send".
- Body 14px `#55605c`: "Letters, numbers, arrows, Space, Enter and F-keys work."
- Same action bar with "Cancel".

**Behavior:** on keypress the dashed slot becomes a solid key cap with the captured key, the dialog closes, and the new row appears in the bindings list. Two-step progress in the title bar is what replaces the current pair of unlabeled sequential dialogs.

### 9. Add game (mock `1e`, `data-screen-label="Add game dialog"`)

480 wide, header bar title "Add game". Content padding `18px 22px 0`, `gap: 12px`:
- Label "Running now", 13px `#6f7679`.
- **Detected list card**: border `#e4e0dc`, radius 8; rows padding `11px 13px`, separated `1px solid #eeebe8`; each row = 24×24 avatar (radius 5; first row tinted `#e8f4ef`/`#17916b`, others `#f2f1f0`/`#6f7679`), name 14.7px with AppID in `#9aa09d` 13px, then an "Add" button (first row primary `#17916b` white 12.5px/700 padding `4px 10px` radius 5; others secondary with `#d6d1cd` border).
- **Manual row**, `gap: 10px`: a `Gtk.Entry` filling the width, padding `8px 10px`, border `#cfcac6`, radius 6, placeholder "Or paste a Steam AppID" in `#9a9996` 13.5px; then a secondary "Add" button (padding `8px 14px`).
- Action bar `margin-top: 16px`, `border-top: 1px solid #eeebe8`, padding `12px 20px`, right-aligned "Close".

This merges the current two separate buttons ("Add game I'm playing now" and "Add by AppID…") into one dialog: detection first, manual entry as the fallback underneath.

### 10. Preferences (mock `1e`, `data-screen-label="Preferences"`) — new screen

480 wide, header bar title "Preferences". Content padding `16px 20px 18px`, `gap: 16px`, body 14.7px:
- **Switch card**: border `#e4e0dc`, radius 8; rows padding `12px 14px` separated `1px solid #eeebe8`; label flexes, `Gtk.Switch` (40×22, on `#17916b`/white knob, off `#dcd8d4`/white knob) on the right. Rows: "Keep window above games" (on), "Start daemon at login" (on), "Show tray icon" (off).
- **Appearance**, label 13px `#6f7679`, then a segmented control: track padding 3, background `#f2f1f0`, border `#e4e0dc`, radius 7, `gap: 4px`; three equal segments padding 6, radius 5, 13.5px; selected = white, border `#dcd8d4`, 700. Options: System (selected), Light, Dark. Implement as a `Gtk.Box` of linked `Gtk.RadioButton`s in `draw-indicator=False` mode, or a `Gtk.StackSwitcher`-styled box.
- **Bottom row**, `padding-top: 4px`, `gap: 10px`: left 13px `#6f7679` "Daemon running · Logitech G502 HERO"; right secondary button "Run health check" (padding `7px 13px`, radius 6, border `#d6d1cd`, 13.5px).

The health check is not gone — it moves here as an on-demand action, since after first run it is a diagnostic, not an onboarding step.

### 11. Empty state (mock `1e`, `data-screen-label="Empty state"`)

Shown in the content pane when the selected profile has no bindings. Centered, padding `42px 28px 46px`, `gap: 10px`:
- Headline 18px/700: "No bindings for this game".
- Body 14px `#55605c`, `max-width: 300px`, line-height 1.5: "Press **Add binding**, click a mouse button, then the key it should send." ("Add binding" bold.)
- Primary button "Add binding", `margin-top: 6px`, padding `8px 16px`, radius 6, `#17916b`, white, 13.5px/700.

### 12. Error state (mock `1e`, `data-screen-label="Error state"`)

**Inline banner above the bindings list — not a dialog.** Content padding `16px 18px`, `gap: 12px`:
- Banner: `display: flex; gap: 11px`, padding `13px 14px`, radius 8, background `#fdf4e7`, border `1px solid #ecd7b0`. Leading `!` glyph `#a9741a`/700. Then a column, `gap: 8px`: title 14px/700 "Remapping is paused"; body 13px `#55605c` line-height 1.5 "The daemon can't reach your mouse. Restarting it usually fixes this."; a button row `gap: 8px` with primary "Restart daemon" (padding `6px 12px`, radius 6, 13px/700) and secondary "Details" (border `#d6d1cd`, 13px).
- Note beneath, 12.5px `#8a908d`: "Errors appear as one banner above the bindings list. No modal, no stacked message dialogs."

**Behavior:** at most one banner at a time; a new condition replaces the current one. "Details" expands the raw diagnostic text in place (a `Gtk.Expander`), it does not open a window. When the banner is visible the header-bar status pill switches to the paused treatment (warning colors, copy "Remapping paused").

## Interactions & behavior

**Navigation**
- Selecting a sidebar row swaps the content pane. Use a `Gtk.Stack` with `crossfade`, 150ms — do not rebuild the pane.
- The wizard is a step machine over a `Gtk.Stack` (`slide-left`/`slide-right`, 200ms). Progress segments and the "Step N of 4" counter update together.
- Add-binding is a two-step flow inside one dialog, not two dialogs. Same stack pattern.

**Hover / active / focus**
- Secondary buttons on hover: light `#faf9f8`, dark `#32363a`. Active: light `#f2f1f0`, dark `#26292b`.
- Primary buttons on hover: `#148060`. Active: `#0f6e50`.
- Unselected sidebar rows on hover: light `#efedeb`, dark `#26292b`. The selected row does not change on hover.
- The row `✕` and `⋯` buttons are invisible-until-hover on their row (opacity 0 → 1, 100ms); keep them keyboard-focusable regardless.
- Focus ring: 2px `#17916b` at 40% alpha, offset 1px, radius matching the control.
- Destructive menu item on hover: light `#fdeceb`, dark `#3a2523`; text stays `#b3261e`.

**Waiting states**
- Add-binding step 1's circle pulses: `box-shadow: 0 0 0 0 rgba(23,145,107,.35)` → `0 0 0 12px rgba(23,145,107,0)`, 1.6s, ease-out, infinite.
- The pending dashed key slot in step 2 pulses its border color between `#17916b` and `#3fae86`, 1.2s.
- Anything that takes a password prompt (wizard step 1, "Restart daemon") disables its button and shows a spinner in place of the label until the `pkexec` call returns.

**Feedback**
- Rename commit shows the confirmation strip for ~2.5s, then fades (200ms).
- Binding add/remove writes immediately; the footer "Saved automatically" is the only save affordance — no Apply/OK.
- Removing a binding is undoable via a 5s inline "Undo" in the footer, or falls back to plain removal if you'd rather not add undo.

**Keyboard**
- `F2` on a focused sidebar row starts rename. `Delete` prompts removal.
- Menu key / Shift+F10 opens the row popover.
- Esc closes any dialog or cancels inline edit. Enter activates the primary action.
- Full tab order through sidebar → primary action → binding rows → footer.

**Responsive**
- The main window may be resized above 900×600: sidebar stays fixed at 250px, content pane flexes, bindings list scrolls in a `Gtk.ScrolledWindow`. Wizard and dialogs are fixed-size.

## State

- `profiles: [{ id (AppID or "default"), display_name, binding_count }]`
- `selected_profile_id`
- `bindings_for_selected: [{ button_id, button_display_name, keycode, key_display_name }]`
- `renaming_profile_id | null`, plus `rename_draft` — the inline entry's text
- `daemon_status: running | stopped | paused`, `active_profile_id`, `device_name`, `session_type`
- `banner: { kind, title, body, actions } | null` — at most one
- `wizard_step: 1..4`, `preflight_results` from `preflight.py`
- `pending_binding: { button_id } | null` during the add-binding flow
- `prefs: { keep_above, start_at_login, tray_icon, appearance: system|light|dark }`

Transitions worth naming: rename → commit clears `renaming_profile_id` and updates `display_name` only; a daemon status change to `paused` sets `banner` and flips the pill; completing wizard step 4 persists a first-run-done flag and opens the main window at 900×600.

Data sources are the ones already in the codebase: `config.py` for profiles/bindings, `daemon.py`/`engine.py` for status and device, `preflight.py` for the check results. No new fetching.

## Assets

None. No images, no bitmaps, no custom-drawn artwork. The glyphs in the mocks (`≡ ⋯ ✕ ★ ◉ → ! – □ ✓ •`) stand in for **stock GTK icon-theme icons** — use the named icons from the user's theme (`open-menu-symbolic`, `view-more-symbolic`, `window-close-symbolic`, `starred-symbolic`, `go-next-symbolic`, `dialog-warning-symbolic`, `object-select-symbolic`), not literal text characters. The 22×22 sidebar avatars are a colored rounded rect with the game's first letter, drawn as a styled `Gtk.Label` — no game artwork is fetched.

Fonts: system UI font only. `DejaVu Sans Mono` (or the system monospace) for key caps and keycodes.

## GTK3 widget mapping

| Design element | GTK3 |
|---|---|
| Window chrome + title/status/menu | `Gtk.HeaderBar` with `custom_title` box; `show_close_button=True` |
| Status pill | `Gtk.Box` + `Gtk.Label`, CSS class `.status-pill` |
| App menu | `Gtk.MenuButton` + `Gtk.Popover` |
| Sidebar profile list | `Gtk.ListBox` with custom row widgets (replaces the current `Gtk.TreeView`) |
| Row overflow menu | `Gtk.MenuButton`/`Gtk.Popover` per row, plus `button-press-event` for right-click |
| Inline rename | swap the row's `Gtk.Label` for a `Gtk.Entry`; `activate` / `focus-out-event` / `key-press-event` for Esc |
| Bindings list | `Gtk.ListBox` in a `Gtk.ScrolledWindow` (replaces the current `Gtk.TreeView`) |
| Button chip / key cap | `Gtk.Label` with CSS classes `.chip` / `.keycap` |
| Pane split | `Gtk.Box` horizontal (fixed 250px sidebar), or `Gtk.Paned` with the handle disabled |
| Screen switching | `Gtk.Stack` (+ `Gtk.StackSwitcher` nowhere — navigation is the list) |
| Wizard | `Gtk.Assistant` if its chrome is acceptable, otherwise a `Gtk.Window` + `Gtk.Stack` and your own action bar (the mocks show the latter) |
| Progress segments | four `Gtk.Box`es with a fixed height and CSS background |
| Toggles | `Gtk.Switch` |
| Segmented control | linked `Gtk.RadioButton`s, `draw_indicator=False`, in a `.linked` box |
| Error banner | `Gtk.InfoBar` restyled, or a plain `Gtk.Box` with CSS (plain box gives you the exact look) |
| Footer strips | `Gtk.Box` with CSS class `.footer-bar` |
| Details expansion | `Gtk.Expander` |
| Theming | one `Gtk.CssProvider` at `APPLICATION` priority; light/dark via a `.dark` class on the toplevel or by swapping providers |

Two structural notes: the current UI's `Gtk.TreeView`s should become `Gtk.ListBox`es — the redesign's two-line rows, per-row buttons, and inline editing are painful in a tree view and natural in a list box. And all six current sidebar buttons disappear as buttons; make sure every one of their actions still has a home (Add game → sidebar footer; Add by AppID → inside Add game; Rename/Remove → row popover; Set up mouse → wizard step 3, reachable again from the app menu; Health check → Preferences).

## Files in this bundle

- `LibreHub Redesign.dc.html` — the redesign. Sections in canvas order: `1a` main window light, `1b` rename popover + inline edit, `1c` main window dark, `1d` wizard steps 1 and 3, `1e` dialogs, preferences, empty and error states. Individual windows are findable by their `data-screen-label` attributes, quoted throughout this README.
- `LibreHub Current UI.dc.html` — recreation of the existing GTK3 UI (main window + all seven current dialogs) for before/after comparison.
- `support.js` — runtime needed to open the two HTML files in a browser. Not part of the design; do not port it.

Open either HTML file directly in a browser. They are static references with no build step.
