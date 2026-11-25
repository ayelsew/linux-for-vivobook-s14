"""COSMIC: volume, brightness and media with generic commands (wpctl, logind, playerctl).

Author: @ayelsew
https://github.com/ayelsew/linux-for-vivobook-s14

These commands don't depend on a desktop, so this file is also the FALLBACK for desktops without their
own *_ctl.py (on those, the on-screen popup may not appear). Contract: see README.md in this folder.
"""

import glob
import math
import os

DESKTOP = "COSMIC"
REQUIRES = ["wpctl", "busctl", "playerctl"]
FALLBACK = True


def volume(ctx, up):
    ctx.run(["wpctl", "set-volume", "-l", str(ctx.volume_max), "@DEFAULT_AUDIO_SINK@",
             ctx.volume_step + ("+" if up else "-")])


def brightness(ctx, up):
    backlights = sorted(glob.glob("/sys/class/backlight/*"))
    if not backlights:
        ctx.log("   no /sys/class/backlight")
        return
    bl = backlights[0]
    try:
        cur = int(open(bl + "/brightness").read())
        mx = int(open(bl + "/max_brightness").read())
    except (OSError, ValueError) as e:
        ctx.log(f"   error reading brightness: {e}")
        return
    step = max(1, round(mx * ctx.brightness_step_pct / 100))
    new = min(mx, max(math.ceil(mx * ctx.brightness_min_pct / 100), cur + (step if up else -step)))
    if new != cur:  # logind lets the active session's user change the brightness without root
        ctx.run(["busctl", "call", "org.freedesktop.login1", "/org/freedesktop/login1/session/auto",
                 "org.freedesktop.login1.Session", "SetBrightness", "ssu", "backlight",
                 os.path.basename(bl), str(new)])


def media(ctx, next_track):
    ctx.run(["playerctl", "next" if next_track else "previous"])
