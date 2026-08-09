#!/usr/bin/env bash
set -euo pipefail

echo "Installing LibreHub..."
pipx install --force . 2>/dev/null || pip install --user .

# udev rule + input group (privileged, one-time)
sudo install -m 0644 packaging/99-librehub-uinput.rules /etc/udev/rules.d/99-librehub-uinput.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
if ! id -nG "$USER" | tr ' ' '\n' | grep -qx input; then
  sudo usermod -aG input "$USER"
  echo "Added $USER to the 'input' group — LOG OUT and back in for it to take effect."
fi

# user service + desktop entry
mkdir -p ~/.config/systemd/user ~/.local/share/applications
install -m 0644 packaging/librehub-daemon.service ~/.config/systemd/user/librehub-daemon.service
install -m 0644 packaging/librehub.desktop ~/.local/share/applications/librehub.desktop
systemctl --user daemon-reload
systemctl --user enable --now librehub-daemon.service || \
  echo "Service will start after next login (input group / graphical session)."

echo "Done. If prompted about the 'input' group, log out and back in."
