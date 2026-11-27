#!/usr/bin/env python3
# Author: @ayelsew
# https://github.com/ayelsew/linux-for-vivobook-s14
"""signals.py: write the test signals used for speaker measurements, always byte-identical.

What: pink-6s.wav, 6 s of pink noise at -20 dBFS RMS with 0.1 s fades, 48 kHz, 16-bit stereo (same signal in both
channels).
How: white noise from Python's random with a fixed seed, through Paul Kellet's pink filter. The Mersenne Twister is
the same on every platform, so Linux and Windows get the same file (check the SHA-256 printed at the end).
Why: comparing two systems (or two settings) needs the exact same test signal on both.

Usage: python3 -I signals.py [OUTPUT_DIR]   (default: the current directory)
"""

import hashlib
import math
import random
import struct
import sys
import wave
from pathlib import Path


def pink(path, seconds=6, rms_db=-20.0, fs=48000):
    random.seed(3)
    n = seconds * fs
    b = [0.0] * 7
    xs = []
    for _ in range(n):
        w = random.uniform(-1, 1)
        b[0] = 0.99886 * b[0] + w * 0.0555179
        b[1] = 0.99332 * b[1] + w * 0.0750759
        b[2] = 0.96900 * b[2] + w * 0.1538520
        b[3] = 0.86650 * b[3] + w * 0.3104856
        b[4] = 0.55000 * b[4] + w * 0.5329522
        b[5] = -0.7616 * b[5] - w * 0.0168980
        xs.append(b[0] + b[1] + b[2] + b[3] + b[4] + b[5] + b[6] + w * 0.5362)
        b[6] = w * 0.115926
    g = 10 ** (rms_db / 20) / math.sqrt(sum(x * x for x in xs) / n)
    fade = int(0.1 * fs)
    out = bytearray()
    for i, x in enumerate(xs):
        e = min(1, i / fade, (n - 1 - i) / fade)
        v = max(-32767, min(32767, int(x * g * e * 32767)))
        out += struct.pack("<hh", v, v)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(fs)
        f.writeframes(bytes(out))


def main():
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / "pink-6s.wav"
    pink(p)
    print(p, "sha256", hashlib.sha256(p.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
