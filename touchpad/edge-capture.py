#!/usr/bin/env python3
"""edge-capture.py — temporary tool: records where each edge gesture should start and end.

For each gesture it asks you to swipe a few times, covering the WHOLE part of the edge where the gesture
should work (and only that part). It records the start and end of every one-finger stroke and prints a
summary with the ranges, to set the zones of touchpad-edge-gestures.py.

Author: @ayelsew
https://github.com/ayelsew/linux-for-vivobook-s14

Usage (needs read access to the touchpad):
    sudo python3 -I edge-capture.py
Stop the gestures daemon first if it is installed (gtouchpad off), so swipes don't change volume etc.
"""

import fcntl
import glob
import os
import select
import struct
import sys
import time

TOUCHPAD_NAME = "ASCP1200:00 093A:3016 Touchpad"

STEPS = [
    ("left",   "LEFT edge (volume)",
     "Slide up and down along the left edge. Start strokes from the LOWEST and the HIGHEST\n"
     "   points where volume SHOULD work."),
    ("right",  "RIGHT edge (brightness)",
     "Slide up and down along the right edge. Start strokes from the LOWEST and the HIGHEST\n"
     "   points where brightness SHOULD work."),
    ("top",    "TOP edge (media)",
     "Slide left and right along the top edge. Start strokes from the LEFTMOST and the RIGHTMOST\n"
     "   points where media SHOULD work."),
    ("corner", "TOP-RIGHT corner (opens a program)",
     "Slide from the top-right corner toward the center. Start from the edges of the area that\n"
     "   should count as 'corner'."),
]

EV_SYN, EV_ABS = 0, 3
SYN_REPORT, SYN_DROPPED = 0, 3
ABS_MT_SLOT, ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID = 0x2F, 0x35, 0x36, 0x39
EVENT = struct.Struct("llHHi")  # struct input_event (x86_64)


def find_device():
    for p in sorted(glob.glob("/sys/class/input/event*")):
        try:
            with open(p + "/device/name") as f:
                if f.read().strip() == TOUCHPAD_NAME:
                    return "/dev/input/" + os.path.basename(p)
        except OSError:
            pass
    return None


def abs_range(fd, code):
    req = (2 << 30) | (24 << 16) | (ord("E") << 8) | (0x40 + code)  # EVIOCGABS
    _, lo, hi, *_ = struct.unpack("6i", fcntl.ioctl(fd, req, bytes(24)))
    return lo, hi


class Recorder:
    """Turns raw events into finished one-finger strokes: (start_x, start_y, end_x, end_y), 0..1."""

    def __init__(self, xr, yr):
        self.xr, self.yr = xr, yr
        self.slots, self.slot = {}, 0
        self.stroke = None      # [tid, sx, sy, ex, ey, multi]
        self.dropped = False

    def norm(self, x, y):
        return ((x - self.xr[0]) / (self.xr[1] - self.xr[0]), (y - self.yr[0]) / (self.yr[1] - self.yr[0]))

    def feed(self, typ, code, val):
        """Returns a finished stroke or None."""
        if typ == EV_SYN and code == SYN_DROPPED:
            self.dropped = True
            return None
        if self.dropped:
            if typ == EV_SYN and code == SYN_REPORT:
                self.dropped, self.stroke = False, None
                self.slots.clear()
                print("   (events lost, stroke discarded)")
            return None
        if typ == EV_ABS:
            if code == ABS_MT_SLOT:
                self.slot = val
            else:
                s = self.slots.setdefault(self.slot, [-1, 0, 0])
                if code == ABS_MT_TRACKING_ID:
                    s[0] = val
                elif code == ABS_MT_POSITION_X:
                    s[1] = val
                elif code == ABS_MT_POSITION_Y:
                    s[2] = val
            return None
        if not (typ == EV_SYN and code == SYN_REPORT):
            return None

        active = [s for s in self.slots.values() if s[0] != -1]
        if self.stroke is None:
            if len(active) == 1:
                tid, x, y = active[0]
                self.stroke = [tid, x, y, x, y, False]
            return None
        if len(active) > 1:
            self.stroke[5] = True            # more than one finger: stroke will be ignored
        own = [s for s in active if s[0] == self.stroke[0]]
        if own:
            self.stroke[3], self.stroke[4] = own[0][1], own[0][2]
            return None
        # The stroke's finger was lifted
        tid, sx, sy, ex, ey, multi = self.stroke
        self.stroke = None
        if multi:
            print("   (more than one finger, stroke ignored)")
            return None
        return (*self.norm(sx, sy), *self.norm(ex, ey))


def pct(v):
    return f"{v * 100:5.1f}%"


def summary(key, strokes):
    if not strokes:
        return [f"{key}: no strokes"]
    sx = [s[0] for s in strokes]
    sy = [s[1] for s in strokes]
    ex = [s[2] for s in strokes]
    ey = [s[3] for s in strokes]
    lines = [f"{key}: {len(strokes)} strokes",
             f"  start X {pct(min(sx))} .. {pct(max(sx))}   start Y {pct(min(sy))} .. {pct(max(sy))}",
             f"  end   X {pct(min(ex))} .. {pct(max(ex))}   end   Y {pct(min(ey))} .. {pct(max(ey))}"]
    if key in ("left", "right"):
        lines.append(f"  used along the edge (Y, start and end): {pct(min(sy + ey))} .. {pct(max(sy + ey))}")
    elif key == "top":
        lines.append(f"  used along the edge (X, start and end): {pct(min(sx + ex))} .. {pct(max(sx + ex))}")
    return lines


def main():
    dev = find_device()
    if not dev:
        sys.exit(f"Touchpad '{TOUCHPAD_NAME}' not found")
    try:
        fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
    except PermissionError:
        sys.exit(f"No permission to read {dev}. Run: sudo python3 -I {os.path.basename(sys.argv[0])}")
    xr, yr = abs_range(fd, ABS_MT_POSITION_X), abs_range(fd, ABS_MT_POSITION_Y)
    print(f"Touchpad {dev}: X {xr[0]}–{xr[1]}, Y {yr[0]}–{yr[1]}")
    print("Positions are in % of the touchpad: X 0% = left, 100% = right; Y 0% = top, 100% = bottom.")

    results = {}
    for key, title, howto in STEPS:
        print(f"\n=== {title}\n   {howto}\n   Use ONE finger. Press Enter when done (Enter with no strokes = skip).")
        rec = Recorder(xr, yr)
        strokes = []
        while True:
            ready, _, _ = select.select([fd, sys.stdin], [], [])
            if sys.stdin in ready:
                sys.stdin.readline()
                break
            try:
                data = os.read(fd, EVENT.size * 64)
            except BlockingIOError:
                continue
            for off in range(0, len(data) - EVENT.size + 1, EVENT.size):
                _, _, typ, code, val = EVENT.unpack_from(data, off)
                s = rec.feed(typ, code, val)
                if s:
                    strokes.append(s)
                    print(f"   #{len(strokes):<2} start X {pct(s[0])} Y {pct(s[1])}  →  "
                          f"end X {pct(s[2])} Y {pct(s[3])}")
        results[key] = strokes
    os.close(fd)

    lines = [f"edge-capture {time.strftime('%Y-%m-%d %H:%M:%S')}  touchpad X {xr[0]}–{xr[1]}, Y {yr[0]}–{yr[1]}", ""]
    for key, _, _ in STEPS:
        lines += summary(key, results[key]) + [""]
    lines.append("Raw strokes (start_x start_y end_x end_y, fraction 0..1):")
    for key, _, _ in STEPS:
        for s in results[key]:
            lines.append(f"  {key:6} " + " ".join(f"{v:.4f}" for v in s))
    text = "\n".join(lines) + "\n"

    print("\n" + "=" * 70 + "\n" + text)
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, time.strftime("edge-capture-%Y%m%d-%H%M%S.txt"))
    with open(out, "w") as f:
        f.write(text)
    uid, gid = os.environ.get("SUDO_UID"), os.environ.get("SUDO_GID")
    if uid and gid:  # run with sudo: give the file back to the real user
        for p in (out_dir, out):
            os.chown(p, int(uid), int(gid))
    print(f"Saved to logs/{os.path.basename(out)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled")
