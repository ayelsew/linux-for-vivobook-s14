#!/usr/bin/env python3
# Author: @ayelsew
# https://github.com/ayelsew/linux-for-vivobook-s14
"""analyze.py: third-octave spectrum of mic recordings (phone or USB mic), and the difference between two of them.

What: prints the level of each third-octave band (25 Hz - 16 kHz) of a mono WAV (float32 from the phone page, or
16/24-bit PCM). With two files it also prints B - A per band, which is what an A/B test needs: the phone mic's own
response is the same in both, so it cancels out.

How: Welch average of Hann-windowed FFTs (pure Python radix-2 FFT, 8192 points, 50 % overlap), then the power of
the FFT bins inside each band is summed. Levels are dBFS of the recording, not acoustic SPL.

Why: hearing "less bass" or "cleaner" is hard to trust; band levels show it, and a silence recording shows which
bands are only room noise.

Usage:
    python3 -I analyze.py A.wav [B.wav] [--from SECONDS] [--to SECONDS]
"""

import argparse
import cmath
import math
import struct
import sys
from pathlib import Path

N = 8192
BANDS = [25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000,
         2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000]


def read_wav(path):
    """Mono samples as floats (first channel), and the sample rate."""
    raw = Path(path).read_bytes()
    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        sys.exit(f"not a WAV file: {path}")
    pos, fmt, data = 12, None, None
    while pos + 8 <= len(raw):
        cid, size = raw[pos:pos + 4], struct.unpack("<I", raw[pos + 4:pos + 8])[0]
        body = raw[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", body[:16])
        elif cid == b"data":
            data = body
        pos += 8 + size + (size & 1)
    tag, ch, rate, _, align, bits = fmt
    width = bits // 8
    frames = len(data) // align
    xs = []
    for i in range(frames):
        b = data[i * align:i * align + width]
        if tag == 3:
            xs.append(struct.unpack("<f", b)[0])
        else:
            xs.append(int.from_bytes(b, "little", signed=True) / float(1 << (bits - 1)))
    return xs, rate


def fft(a):
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    size = 2
    while size <= n:
        w = cmath.exp(-2j * math.pi / size)
        half = size // 2
        for start in range(0, n, size):
            wk = 1
            for k in range(start, start + half):
                t = wk * a[k + half]
                a[k + half] = a[k] - t
                a[k] = a[k] + t
                wk *= w
        size *= 2
    return a


def bands(xs, rate):
    win = [0.5 - 0.5 * math.cos(2 * math.pi * i / N) for i in range(N)]
    norm = sum(w * w for w in win)
    psd = [0.0] * (N // 2)
    count = 0
    for start in range(0, len(xs) - N + 1, N // 2):
        spec = fft([complex(xs[start + i] * win[i]) for i in range(N)])
        for k in range(N // 2):
            psd[k] += abs(spec[k]) ** 2
        count += 1
    if not count:
        sys.exit("recording too short (needs at least 0.2 s)")
    out = []
    for fc in BANDS:
        lo, hi = fc / 2 ** (1 / 6), fc * 2 ** (1 / 6)
        p = sum(psd[k] for k in range(1, N // 2) if lo <= k * rate / N < hi)
        p = 2 * p / (count * norm * N)  # sine of amplitude A gives A^2/2, like RMS^2
        out.append(10 * math.log10(p) if p > 0 else -150.0)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path, nargs="?")
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float)
    args = ap.parse_args()

    results = []
    for p in [args.a] + ([args.b] if args.b else []):
        xs, rate = read_wav(p)
        xs = xs[int(args.t0 * rate):int(args.t1 * rate) if args.t1 else None]
        results.append(bands(xs, rate))
        print(f"{p.name}: {len(xs) / rate:.1f} s at {rate} Hz")

    head = f"{'band Hz':>8} {'A dBFS':>8}" + (f" {'B dBFS':>8} {'B-A dB':>7}" if args.b else "")
    print(head)
    for i, fc in enumerate(BANDS):
        line = f"{fc:>8g} {results[0][i]:>8.1f}"
        if args.b:
            line += f" {results[1][i]:>8.1f} {results[1][i] - results[0][i]:>+7.1f}"
        print(line)


if __name__ == "__main__":
    main()
