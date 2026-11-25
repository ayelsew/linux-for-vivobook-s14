# Desktop integrations

The daemon (`touchpad-edge-gestures.py`) detects the gestures. The files in this folder decide **what each
gesture does** on each desktop environment, so the result looks like the Fn keys (with the on-screen popup).

At start, the daemon loads every `*_ctl.py` here and picks the one whose `DESKTOP` matches
`XDG_CURRENT_DESKTOP`. If none matches, it uses the one with `FALLBACK = True` and logs an invitation to
contribute. `gtouchpad install` reads the same files to show if your desktop is supported and to check the
commands in `REQUIRES`.

| File | Desktop | How |
|---|---|---|
| [kde_ctl.py](kde_ctl.py) | KDE Plasma | KDE global shortcuts (same as the Fn keys) |
| [cosmic_ctl.py](cosmic_ctl.py) | COSMIC, and fallback | `wpctl`, logind, `playerctl` |

## Contract

A `<name>_ctl.py` file must define:

```python
DESKTOP = "KDE"                   # name as in $XDG_CURRENT_DESKTOP (case does not matter)
REQUIRES = ["busctl", "wpctl"]    # commands it calls, on ONE line (gtouchpad reads it)
FALLBACK = False                  # optional; True = used when no other file matches

def volume(ctx, up): ...          # up: True = louder, False = quieter
def brightness(ctx, up): ...      # up: True = brighter, False = darker
def media(ctx, next_track): ...   # next_track: True = next, False = previous
```

Each function is called once per step of the gesture, in a background thread. `ctx` gives:

| Name | What it is |
|---|---|
| `ctx.run(cmd)` | Run a command (list of strings). Respects `--dry-run`, never raises, 3 s timeout |
| `ctx.log(msg)` | Write to the daemon log (`journalctl --user -u touchpad-edge-gestures`) |
| `ctx.volume_step` | Volume step, e.g. `"5%"` |
| `ctx.volume_max` | Highest volume allowed, e.g. `1.0` (100 %): don't go above it |
| `ctx.brightness_step_pct` | Brightness step, % of the maximum |
| `ctx.brightness_min_pct` | Lowest brightness allowed, % of the maximum |

Use only the Python standard library.

## Adding your desktop

1. Copy `cosmic_ctl.py` to `<yourdesktop>_ctl.py` and set `DESKTOP` to the value of `echo $XDG_CURRENT_DESKTOP`.
2. Change the three functions to use your desktop's own way (the one that shows the popup).
3. Test without changing anything: `python3 -I touchpad-edge-gestures.py --dry-run -v`
4. Open a pull request at https://github.com/ayelsew/linux-for-vivobook-s14

---

Author: [@ayelsew](https://github.com/ayelsew)
