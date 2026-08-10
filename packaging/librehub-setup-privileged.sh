#!/usr/bin/env bash
# LibreHub one-time privileged setup — intended to be run as root via pkexec:
#
#   pkexec .../packaging/librehub-setup-privileged.sh <repo_dir> <target_user>
#
# Does ONLY the steps that need root, idempotently, so it is safe to re-run:
#   1. install missing system packages (python3-evdev, ratbagd)
#   2. install the /dev/uinput udev rule and reload udev
#   3. add the target user to the 'input' group
#
# Everything user-owned (wrappers, desktop files, systemd --user service) is
# left to install.sh so this never creates root-owned files in $HOME.
set -euo pipefail

REPO="${1:?usage: $0 <repo_dir> <target_user>}"
USER_NAME="${2:?usage: $0 <repo_dir> <target_user>}"

echo "librehub-setup: repo=$REPO user=$USER_NAME"

# --- 1. system packages (only if missing) -----------------------------------
missing=""
command -v ratbagctl >/dev/null 2>&1 || missing="$missing ratbagd"
python3 -c 'import evdev' >/dev/null 2>&1 || missing="$missing python3-evdev"
if [ -n "$missing" ]; then
  echo "librehub-setup: installing packages:$missing"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  # shellcheck disable=SC2086
  apt-get install -y $missing
else
  echo "librehub-setup: packages already present"
fi

# --- 2. udev rule for /dev/uinput -------------------------------------------
RULE=/etc/udev/rules.d/99-librehub-uinput.rules
if [ ! -f "$RULE" ]; then
  echo "librehub-setup: installing udev rule"
  install -m 0644 "$REPO/packaging/99-librehub-uinput.rules" "$RULE"
  udevadm control --reload-rules && udevadm trigger || true
  # Make sure the module is present now (the rule uses static_node for boot).
  modprobe uinput 2>/dev/null || true
else
  echo "librehub-setup: udev rule already installed"
fi

# --- 3. input group membership ----------------------------------------------
if id -nG "$USER_NAME" | tr ' ' '\n' | grep -qx input; then
  echo "librehub-setup: $USER_NAME already in 'input' group"
else
  echo "librehub-setup: adding $USER_NAME to 'input' group"
  usermod -aG input "$USER_NAME"
  echo "librehub-setup: NOTE — log out and back in for the group to take effect"
fi

echo "librehub-setup: done"
