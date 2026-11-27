#!/usr/bin/env python3
# Author: @ayelsew
# https://github.com/ayelsew/linux-for-vivobook-s14
"""musictest.py: build a music test file for Linux vs Windows A/B recordings, and check that it plays bit-exact.

What:
  build  Picks the busiest 25 s of each song (bass, mids and cymbals all strong) and writes music-test.wav:
         1 s silence, sync chirp, 1 s silence, excerpt 1, 1.5 s silence, chirp, 1 s silence, excerpt 2, 1.5 s silence.
         The samples of each excerpt are copied unchanged from the song (only 10 ms fades at the cut points), in the
         song's own format (48 kHz, 24-bit stereo from record-loop.sh). It also writes music-test.json with the
         layout, the chosen times and the SHA-256 of every file, so the other system can check it has the same bytes.
  null   Compares a recording of the effects' INPUT (Linux: easyeffects_sink) with music-test.wav: finds the offset
         and reports whether every sample is identical. That proves the signal entering EasyEffects is the file.

How: excerpt score = mean level (dB) over the window of three bands: low (2nd-order low-pass 150 Hz), all, and high
(2nd-order high-pass 5 kHz), summed, on 0.5 s blocks of the mono mix. The first and last 10 s of a song are skipped.
The chirp is a 0.3 s log sweep 300 Hz - 6 kHz at -12 dBFS, inside the speakers' range, so a mic recording can be
aligned on it.
Why: comparing the sound of two systems needs the exact same music on both, aligned to the sample.

The songs are copies of copyrighted music: keep them and music-test.wav local (logs/ is gitignored).

Usage:
    python3 -I musictest.py build SONG1.wav SONG2.wav [--out DIR] [--seconds 25]
    python3 -I musictest.py null music-test.wav RECORDING.wav
"""

import argparse
import array
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

BLOCK = 0.5  # seconds, scoring resolution


def read_pcm(path):
    """(rate, channels, bits, interleaved int samples, data bytes) of a 16/24/32-bit PCM or float32 WAV."""
    raw = Path(path).read_bytes()
    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        sys.exit(f"not a WAV file: {path}")
    pos, fmt, data = 12, None, None
    while pos + 8 <= len(raw):
        cid, size = raw[pos:pos + 4], struct.unpack("<I", raw[pos + 4:pos + 8])[0]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", raw[pos + 8:pos + 24])
        elif cid == b"data":
            data = raw[pos + 8:pos + 8 + size]
        pos += 8 + size + (size & 1)
    tag, ch, rate, _, _, bits = fmt
    if tag == 0xFFFE:  # WAVE_FORMAT_EXTENSIBLE: the real tag is the first 2 bytes of the sub-format GUID
        i = raw.find(b"fmt ")
        tag = struct.unpack("<H", raw[i + 8 + 24:i + 8 + 26])[0]
    if tag == 3 and bits == 32:  # float: scale to 24-bit ints so it compares with a 24-bit file
        f = array.array("f")
        f.frombytes(data[:len(data) // 4 * 4])
        return rate, ch, 24, array.array("i", (round(x * 8388608) for x in f)), data
    a = array.array("i")
    if bits == 16:
        h = array.array("h")
        h.frombytes(data[:len(data) // 2 * 2])
        a.extend(h)
    elif bits == 24:
        n = len(data) // 3
        b = bytearray(n * 4)
        b[1::4], b[2::4], b[3::4] = data[0:n * 3:3], data[1:n * 3:3], data[2:n * 3:3]
        a.frombytes(bytes(b))
        a = array.array("i", (x >> 8 for x in a))
    elif bits == 32:
        a.frombytes(data[:len(data) // 4 * 4])
    else:
        sys.exit(f"unsupported {bits}-bit WAV: {path}")
    return rate, ch, bits, a, data


def write_pcm(path, rate, ch, bits, samples):
    width = bits // 8
    out = bytearray()
    for x in samples:
        out += (x & ((1 << bits) - 1)).to_bytes(width, "little")
    head = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(out), b"WAVE", b"fmt ", 16, 1, ch, rate,
                       rate * ch * width, ch * width, bits, b"data", len(out))
    Path(path).write_bytes(head + out)


def biquad(xs, rate, f0, kind):
    """RBJ 2nd-order low-pass or high-pass, Q = 0.707."""
    w = 2 * math.pi * f0 / rate
    al = math.sin(w) / (2 * 0.7071)
    c = math.cos(w)
    if kind == "lp":
        b0, b1, b2 = (1 - c) / 2, 1 - c, (1 - c) / 2
    else:
        b0, b1, b2 = (1 + c) / 2, -(1 + c), (1 + c) / 2
    a0, a1, a2 = 1 + al, -2 * c, 1 - al
    b0, b1, b2, a1, a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
    x1 = x2 = y1 = y2 = 0.0
    ys = array.array("d", bytes(8 * len(xs)))
    for i, x in enumerate(xs):
        y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, x, y1, y
        ys[i] = y
    return ys


def block_db(xs, n):
    out = []
    for k in range(0, len(xs) - n + 1, n):
        s = sum(x * x for x in xs[k:k + n]) / n
        out.append(10 * math.log10(s) if s > 0 else -200.0)
    return out


def pick(path, seconds):
    rate, ch, bits, a, _ = read_pcm(path)
    full = float(1 << (bits - 1))
    mono = array.array("d", (sum(a[i:i + ch]) / (ch * full) for i in range(0, len(a) - ch + 1, ch)))
    n = int(BLOCK * rate)
    bands = [block_db(biquad(mono, rate, 150, "lp"), n), block_db(mono, n),
             block_db(biquad(mono, rate, 5000, "hp"), n)]
    win, skip = int(seconds / BLOCK), int(10 / BLOCK)
    best = None
    for s in range(skip, len(bands[1]) - win - skip + 1):
        score = sum(sum(b[s:s + win]) / win for b in bands)
        if best is None or score > best[0]:
            best = (score, s)
    if best is None:
        sys.exit(f"{path} is too short for a {seconds} s excerpt plus 10 s at each end")
    s = best[1]
    levels = [round(sum(b[s:s + win]) / win, 1) for b in bands]
    return rate, ch, bits, a, s * BLOCK, levels


def chirp(rate, ch, bits, secs=0.3, f1=300.0, f2=6000.0, db=-12.0):
    n = int(secs * rate)
    g = 10 ** (db / 20) * ((1 << (bits - 1)) - 1)
    k = math.log(f2 / f1)
    out = []
    for i in range(n):
        t = i / rate
        ph = 2 * math.pi * f1 * secs / k * (math.exp(t / secs * k) - 1)
        v = round(g * math.sin(ph) * math.sin(math.pi * i / n) ** 2)
        out.extend([v] * ch)
    return out


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(args):
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    picks = []
    for song in args.songs:
        print(f"Scoring {song} ...", flush=True)
        picks.append((song, *pick(song, args.seconds)))
    fmt = {(p[1], p[2], p[3]) for p in picks}
    if len(fmt) != 1:
        sys.exit(f"the songs have different formats {fmt}: record both with record-loop.sh")
    rate, ch, bits = fmt.pop()
    sil = lambda s: [0] * (int(s * rate) * ch)
    fade = int(0.01 * rate)
    samples, layout = sil(1.0), []
    for song, _, _, _, a, start, levels in picks:
        layout.append({"chirp_at": len(samples) // ch / rate})
        samples += chirp(rate, ch, bits) + sil(1.0)
        i0, n = int(start * rate), int(args.seconds * rate)
        ex = list(a[i0 * ch:(i0 + n) * ch])
        for i in range(fade):  # 10 ms linear fades at the cut points
            e = i / fade
            for c in range(ch):
                ex[i * ch + c] = round(ex[i * ch + c] * e)
                ex[(n - 1 - i) * ch + c] = round(ex[(n - 1 - i) * ch + c] * e)
        layout[-1].update({"song": Path(song).name, "song_sha256": sha(song), "song_from": start,
                           "song_to": start + args.seconds, "music_at": len(samples) // ch / rate,
                           "seconds": args.seconds, "levels_db_low_all_high": levels})
        samples += ex + sil(1.5)
    wav = out_dir / "music-test.wav"
    write_pcm(wav, rate, ch, bits, samples)
    info = {"file": wav.name, "sha256": sha(wav), "rate": rate, "channels": ch, "bits": bits,
            "length_s": len(samples) // ch / rate, "chirp": "0.3 s log sweep 300-6000 Hz, -12 dBFS", "parts": layout}
    (out_dir / "music-test.json").write_text(json.dumps(info, indent=2) + "\n")
    for p in layout:
        m, s = divmod(p["song_from"], 60)
        print(f"  {p['song']}: {int(m)}:{s:04.1f} for {p['seconds']} s -> at {p['music_at']:.3f} s in the test file")
    print(f"{wav}  {info['length_s']:.1f} s  sha256 {info['sha256']}")


def null(args):
    rate, ch, _, ref, _ = read_pcm(args.ref)
    rate2, ch2, _, rec, _ = read_pcm(args.rec)
    if (rate, ch) != (rate2, ch2):
        sys.exit(f"format differs: file {rate} Hz {ch} ch, recording {rate2} Hz {ch2} ch")
    first = next(i for i in range(0, len(ref), ch) if ref[i] != 0)  # first non-zero frame of the file
    probe = list(ref[first:first + 64 * ch])
    hits = [j for j in range(0, len(rec) - len(probe) + 1, ch)
            if rec[j] == probe[0] and list(rec[j:j + len(probe)]) == probe]
    if not hits:
        print("No exact match for the start of the file: the signal was changed (volume, resampling or format).")
        sys.exit(1)
    off = hits[0] - first
    n = min(len(ref), len(rec) - off) if off >= 0 else min(len(ref) + off, len(rec))
    worst, bad = 0, 0
    for i in range(max(0, -off), n):
        d = abs(rec[i + off] - ref[i])
        if d:
            bad += 1
            worst = max(worst, d)
    print(f"Offset {off // ch / rate:.4f} s, {n // ch / rate:.1f} s compared.")
    if bad == 0:
        print("BIT-EXACT: every sample of the recording equals the file.")
    else:
        print(f"{bad} samples differ, worst by {worst} (24-bit steps, {20 * math.log10(worst / 8388608):.1f} dBFS).")
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("songs", nargs=2)
    b.add_argument("--out", default=".")
    b.add_argument("--seconds", type=float, default=25)
    n = sub.add_parser("null")
    n.add_argument("ref")
    n.add_argument("rec")
    args = ap.parse_args()
    build(args) if args.cmd == "build" else null(args)


if __name__ == "__main__":
    main()
