#!/usr/bin/env bash
set -euo pipefail

REPO="${1:?usage: $0 <repo_dir> <target_user>}"
USER_NAME="${2:?usage: $0 <repo_dir> <target_user>}"

echo "librehub-setup: repo=$REPO user=$USER_NAME"

if command -v apt-get >/dev/null 2>&1; then
  PM_INSTALL="apt-get install -y"; PKG_RATBAGD="ratbagd"; PKG_EVDEV="python3-evdev"
elif command -v dnf >/dev/null 2>&1; then
  PM_INSTALL="dnf install -y"; PKG_RATBAGD="libratbag-ratbagd"; PKG_EVDEV="python3-evdev"
else
  PM_INSTALL=""; PKG_RATBAGD="ratbagd"; PKG_EVDEV="python3-evdev"
fi

missing=""
command -v ratbagctl >/dev/null 2>&1 || missing="$missing $PKG_RATBAGD"
python3 -c 'import evdev' >/dev/null 2>&1 || missing="$missing $PKG_EVDEV"
if [ -n "$missing" ]; then
  if [ -z "$PM_INSTALL" ]; then
    echo "librehub-setup: no supported package manager (apt/dnf) found; install manually:$missing" >&2
    exit 1
  fi
  echo "librehub-setup: installing packages:$missing"
  [ "${PM_INSTALL%% *}" = "apt-get" ] && { export DEBIAN_FRONTEND=noninteractive; apt-get update; }
  $PM_INSTALL $missing
else
  echo "librehub-setup: packages already present"
fi

RULE=/etc/udev/rules.d/99-librehub-uinput.rules
if [ ! -f "$RULE" ]; then
  echo "librehub-setup: installing udev rule"
  install -m 0644 "$REPO/packaging/99-librehub-uinput.rules" "$RULE"
  udevadm control --reload-rules && udevadm trigger || true
  modprobe uinput 2>/dev/null || true
else
  echo "librehub-setup: udev rule already installed"
fi

if id -nG "$USER_NAME" | tr ' ' '\n' | grep -qx input; then
  echo "librehub-setup: $USER_NAME already in 'input' group"
else
  echo "librehub-setup: adding $USER_NAME to 'input' group"
  usermod -aG input "$USER_NAME"
  echo "librehub-setup: NOTE — log out and back in for the group to take effect"
fi

echo "librehub-setup: done"
