# Changelog

All notable changes to LibreHub are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-08-16

First stable release.

### Added

- Name a game before saving it. Adding a game is now two steps: pick the
  running game or type an AppID, then confirm the name. Nothing is written
  until you press Save, so a wrong pick costs nothing.
- Re-adding a game you already have renames it and keeps its bindings.
- An application icon, installed into the hicolor theme, so LibreHub appears
  properly in the application menu, the taskbar and the window switcher.
- A per-profile menu on every game row for rename, duplicate and remove.

### Changed

- The Add game dialog separates the detected running game from the manual
  AppID box, and the manual button stays disabled until the AppID is valid.
- Profile rows no longer show a binding count.

### Fixed

- Steam games installed through the Flatpak version of Steam are now found,
  so games get their real names instead of "Game 1086940". Libraries on other
  drives are picked up through the Flatpak's own library list.
- The per-profile menu button rendered as a blank square. Its icon was never
  shown because the button opted out of the parent's show-all pass.
- Switching the appearance to light had no effect on desktop themes that ship
  only a dark variant. LibreHub now measures what the theme actually renders
  and falls back to Adwaita when the desktop theme cannot honour the request.
  Choosing "system" restores the original theme, not just its dark setting.
- Window icons are now correct on Wayland, where the compositor matches a
  window to its desktop entry by application ID rather than by an icon
  property.
- The theme module pinned the wrong GDK version when imported before the
  editor, which could fail depending on import order.
