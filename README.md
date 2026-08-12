# LibreHub

**A free Logitech G HUB alternative for Linux, focused on per game mouse button remapping.**

LibreHub lets you assign your gaming mouse buttons to keyboard keys, with a different set for every game. When you launch a Steam game, LibreHub switches to that game's buttons automatically. When you close it, everything goes back to normal. No manual reconfiguring between titles.

If you moved to Linux and found that Logitech G HUB does not work, and you missed the one feature you actually used every day, this is built to bring that feature back.

Works with the Logitech G502 and other Logitech gaming mice, plus any mouse that ratbagd supports.

## Why this exists

Logitech G HUB has no real Linux version. The part most gamers relied on was simple. You set your side buttons to do one thing in one game and something else in another, and it just happened when you switched games. On Linux there was no easy way to get that back.

The tools that come close each miss something:

* `input-remapper` can remap buttons, but it changes them everywhere at once. There is no per game switching.
* `ratbagd` and Piper write profiles onto the mouse itself, but you only get about five of them and you have to switch by hand.

LibreHub fills that gap. You get as many game profiles as you want, and switching happens on its own based on the Steam game you are playing.

## What you need

* **A mouse:** any Logitech gaming mouse with programmable buttons, or another mouse that ratbagd supports.
* **Your display server:** X11 gives the most precise switching. Wayland works too, with a slightly simpler switching method described further down.
* **Steam** on Linux.
* **Python** 3.10 or newer.
* **A few system packages.** The installer checks for these and tells you the exact names for your distro if any are missing.

| What it is for | Debian, Ubuntu, Mint (apt) | Fedora, RHEL (dnf) |
| --- | --- | --- |
| Python GTK3 bindings | `python3-gi` | `python3-gobject` |
| GTK3 data | `gir1.2-gtk-3.0` | `gtk3` |
| The `ratbagctl` tool | `ratbagd` | `libratbag-ratbagd` |
| evdev bindings | `python3-evdev` | `python3-evdev` |
| PolicyKit, usually already installed | `policykit-1` | `polkit` |

Fedora, all in one line:

```bash
sudo dnf install python3-gobject gtk3 python3-evdev libratbag-ratbagd
```

## Installing it

```bash
./install.sh
```

Here is what that does:

1. Installs the `librehub` and `librehub-daemon` commands.
2. Adds a udev rule so the background helper can reach `/dev/uinput`. This needs `sudo`.
3. Adds your user to the `input` group. This also needs `sudo`.
4. Sets up the background helper as a systemd user service and starts it.

**One important note.** After the install finishes, log out and log back in. The `input` group only takes effect on a fresh login. The helper starts on its own once you are back in.

### The built in setup and health check

The app has a Setup and Health check panel that does all of the above for you and tells you plainly if something is half finished. It opens by itself the first time you run the app, or any time something is not ready. You can also open it whenever you want from the **Setup / Health check** button.

It checks each requirement and offers a one click fix where it can:

| Check | Fix it offers |
|-------|-------------|
| System packages | Runs the setup with a single password prompt |
| The `/dev/uinput` rule | Runs the setup |
| The `input` group, both joined and active | Joins you, then prompts you to log out and back in |
| The helper running and remapping | Start or restart the helper |
| Mouse found and buttons assigned | Set up the mouse |

That "joined the group but not active until you log back in" case is the most common first time snag, so the app calls it out clearly.

Prefer the terminal? Run the same checks there:

```bash
librehub-doctor
```

## Using it

### Set up your mouse once

Each button you want to use needs to send a unique signal that nothing else on your system uses. LibreHub handles this with a guided dialog so you do not have to think about it:

1. Launch the app:

   ```bash
   librehub
   ```

2. Click **Set up mouse** in the left pane. LibreHub scans your mouse and lists each button. Tick the ones you want to manage. It leaves your normal left, right, and middle clicks alone.

3. Click OK. LibreHub programs the chosen buttons into your mouse and confirms when it is done.

4. Restart the helper if it asks you to, either with the button in the dialog or:

   ```bash
   systemctl --user restart librehub-daemon
   ```

After this, the **Add binding** flow can see those buttons.

### Set up a game

1. Open the app:

   ```bash
   librehub
   ```

   You get a game list on the left and a table of button bindings on the right.

2. Add the game. While the Steam game is open and focused, click **Add game I'm playing now** and LibreHub detects it. Or click **Add by AppID** and type the Steam AppID, which you can look up at steamdb.info.

3. Click the game in the left list to edit it.

4. Click **Add binding**, then press the physical mouse button you want to use. A new row appears for it.

5. Click the **Key** cell and type the key you want that button to send, like `m`, `4`, `space`, or `q`. Press Enter.

6. Repeat for the other buttons, then click **Save**.

### Automatic switching

Once a game is set up, LibreHub watches which game has focus and turns on that game's buttons when it launches. When no set up game is focused, it falls back to your default buttons.

**X11 and Wayland.** On X11, LibreHub reads exactly which window is focused, so your buttons apply only while the game is actually in front. Wayland does not let apps ask which window is focused without special permission, so there LibreHub uses a simpler rule: if exactly one game you have set up is running, it turns that game's buttons on. It figures out which session you are in and logs the mode it chose. Two small things to know on Wayland: your buttons stay on while the game is running even if you tab away, and if two set up games run at the same time it cannot tell which you mean, so it uses your default.

## How it works

LibreHub splits the job into two simple parts.

**The signal.** Each managed button is set to send a unique function key that nothing else uses, one of F13 through F24. These live in an always on profile on the mouse itself, which is how LibreHub gets around the roughly five profile limit built into the hardware. Your normal clicks and scroll wheel are untouched.

**The translation.** A small background helper watches for those function keys coming in, looks up the buttons for whatever game you are playing, and sends the real keys you chose. It checks for a game switch about twice a second. It never touches your mouse movement or your clicks, only the button to key translation.

## What it does not do yet

* One key per button for now, not full macros or key combos.
* Steam games only. Other games need manual setup for now.
* Logitech and ratbagd mice only. Broader mouse support is planned.
* Wayland switching is by running game rather than by focused window. X11 has the precise version.
* No hot plug rediscovery yet. If you unplug and replug your mouse mid session, restart the helper with `systemctl --user restart librehub-daemon`.

## What is coming

* Mouse hot plug support.
* Macros and key combos like Ctrl plus Q.
* Matching non Steam games by window title or process name.
* A universal engine so any mouse works, not just Logitech.
* Precise Wayland focus tracking to replace the running game fallback.

## Frequently asked questions

**Does Logitech G HUB work on Linux?**
Not really. There is no proper Linux build, and the per game button feature most people want has no easy native replacement. LibreHub was made to bring that feature to Linux.

**Is there a Logitech G HUB alternative for Linux?**
Yes. LibreHub is a free and open source one, focused on the per game mouse button remapping that G HUB was known for.

**How do I remap mouse buttons per game on Linux?**
Install LibreHub, set up your mouse once, then add a Steam game and assign keys to your buttons. LibreHub switches to that game's buttons on its own whenever the game is focused.

**Does it work with the Logitech G502?**
Yes. The G502 works, along with other Logitech gaming mice and any mouse that ratbagd supports.

**Does it work on Wayland?**
Yes, with a simpler switching method than on X11. See the switching section above for the details.

## Troubleshooting

Start with the built in **Setup / Health check**, or run `librehub-doctor`. It points at the exact thing that is not ready and offers the fix.

**The app says the helper is not running, but it looks like it is.**
The status updates live, so a startup message usually clears on its own. If it sticks around, start the helper with the commands below.

**It says running but remapping is off.**
The helper is up but could not grab the mouse signal, almost always because the `input` group is not active in this session yet. Log out and back in if you just installed, then restart it:

```bash
systemctl --user restart librehub-daemon
```

**The helper will not start.**

```bash
systemctl --user status librehub-daemon.service
systemctl --user enable --now librehub-daemon.service
```

**Permission errors on `/dev/uinput`.**
Check that you are in the `input` group with `id -nG | grep input`. If you are not, run `install.sh` again and log out and back in.

**Mouse not found.**

```bash
ratbagctl list
journalctl --user -u librehub-daemon.service -f
```

## Contributing

LibreHub is open source. Bug reports, feature ideas, and pull requests are all welcome.

## License

MIT. See `LICENSE`.

## Author

Chris. Built while moving fully off Windows to Linux.
