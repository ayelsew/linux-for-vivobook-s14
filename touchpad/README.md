# Touchpad Gestures for ASUS Vivobook S 14 S5406SA

If you need information about the hardware, look: [Hardware.inf.md](Hardware.inf.md)

If you want to understand how the gestures work, look: [Touchpad gestures.md](Touchpad%20gestures.md)

To install on Linux, run:

```sh
curl -fsSL https://raw.githubusercontent.com/ayelsew/linux-for-vivobook-s14/refs/heads/main/touchpad/install.sh | sh
```

It downloads this repository to a temporary folder and runs the installer. Run it as your normal user (not
with sudo): it asks for your password only to install the udev rule. It works from any shell (bash, zsh,
fish). Want to read it first? The download script is [install.sh](install.sh) and the installer is
[install/gtouchpad.sh](install/gtouchpad.sh).

## Commands

After the installation, `gtouchpad` is available in any terminal:

| Command | What it does |
|---|---|
| `gtouchpad on` | Turn the gestures on (stays on after reboot) |
| `gtouchpad off` | Turn the gestures off (stays off after reboot) |
| `gtouchpad status` | Show if the gestures are on and which program the corner opens |
| `gtouchpad corner` | Change the program opened by the top-right corner gesture (asks, current value filled in) |
| `gtouchpad corner "CMD"` | Set it directly, e.g. `gtouchpad corner systemsettings` |
| `gtouchpad corner ""` | No program: the corner gesture does nothing |
| `gtouchpad uninstall` | Remove everything, including `gtouchpad` itself |
| `gtouchpad help` | Show the help |

To update, run the install command again: your corner program setting is kept.

## Calibration

The gesture zones were measured on my S5406SA. If a gesture starts where it should not, or does not start
where it should, measure your own zones with [edge-capture.py](edge-capture.py):

1. Get the repository and stop the gestures, so your swipes don't change the volume while measuring:
   ```sh
   git clone https://github.com/ayelsew/linux-for-vivobook-s14.git
   cd linux-for-vivobook-s14/touchpad
   gtouchpad off
   ```
2. Run the capture (it needs sudo to read the touchpad):
   ```sh
   sudo python3 -I edge-capture.py
   ```
3. It asks for each gesture in turn: left edge (volume), right edge (brightness), top edge (media) and the
   top-right corner. For each one, swipe with **one finger** a few times, starting from **both ends** of the
   stretch where the gesture should work, then press Enter. Enter with no swipes skips that gesture.
4. At the end it prints a summary and saves it to `logs/edge-capture-<date>.txt`.
5. Copy the values from the summary to the settings at the top of
   [install/touchpad-edge-gestures.py](install/touchpad-edge-gestures.py):

   | Summary line | Setting |
   |---|---|
   | `left`: used along the edge (Y) | `LEFT_Y_RANGE` |
   | `right`: used along the edge (Y) | `RIGHT_Y_RANGE` |
   | `top`: used along the edge (X) | `TOP_X_RANGE` |
   | `left` / `right` / `corner`: start X | `EDGE_X` (width of the side strips) |
   | `top` / `corner`: start Y | `EDGE_Y` (height of the top strip) |

   The values are percentages in the summary and fractions in the settings (22.4% → `0.22`).
6. Install the changed version (this also turns the gestures back on):
   ```sh
   ./install/gtouchpad.sh install
   ```

Don't edit the installed copy in `~/.local/lib/touchpad-edge-gestures/` directly: the next install replaces it.

---

Author: [@ayelsew](https://github.com/ayelsew)
