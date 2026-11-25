"""KDE Plasma: volume, brightness and media through KDE's global shortcuts.

Author: @ayelsew
https://github.com/ayelsew/linux-for-vivobook-s14

Each action invokes the same global shortcut the Fn keys trigger, so KDE changes the value, keeps its own
state in sync and shows its on-screen popup. Contract: see README.md in this folder.
"""

import subprocess

DESKTOP = "KDE"
REQUIRES = ["busctl", "wpctl"]


def _shortcut(ctx, component, name):
    ctx.run(["busctl", "--user", "call", "org.kde.kglobalaccel", f"/component/{component}",
             "org.kde.kglobalaccel.Component", "invokeShortcut", "s", name])


def _current_volume():
    try:
        out = subprocess.run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True,
                             text=True, timeout=3).stdout  # e.g. "Volume: 0.75"
        return float(out.split()[1])
    except (OSError, subprocess.SubprocessError, IndexError, ValueError):
        return None


def volume(ctx, up):
    # KDE can go above 100 % ("Raise maximum volume"): ctx.volume_max protects the speakers.
    if up:
        vol = _current_volume()
        if vol is not None and vol >= ctx.volume_max - 0.001:
            ctx.log(f"   volume already at the allowed maximum ({ctx.volume_max})")
            return
    _shortcut(ctx, "kmix", "increase_volume" if up else "decrease_volume")


def brightness(ctx, up):
    _shortcut(ctx, "org_kde_powerdevil", ("Increase" if up else "Decrease") + " Screen Brightness")


def media(ctx, next_track):
    _shortcut(ctx, "mediacontrol", "nextmedia" if next_track else "previousmedia")
