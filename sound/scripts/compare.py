#!/usr/bin/env python3
# Author: @ayelsew
# https://github.com/ayelsew/linux-for-vivobook-s14
"""compare.py: compare recordings of music-test.wav (Linux vs Windows, preset vs preset) by how they change over time.

What: each take (a digital capture of the effects' output, or a mic recording) is aligned to music-test.wav and cut
into short blocks. For every block and band it measures the gain: take level minus file level. From that it prints,
one column per take:
  - Spectrum: median gain per band, relative to the reference band (the static EQ).
The reference band ("full band" below) is 150 Hz - 20 kHz: these speakers play almost nothing below 150 Hz, and
music has most of its energy there, so a 20 Hz - 20 kHz level would mostly measure bass the speakers cannot play.
  - Movement: p90 - p10 of the block gain. 0 means a fixed EQ; more means the processing reacts to the music
    (regulator, Intelligent EQ, limiter).
  - Slope: block gain against the block's input level in that band, in dB per dB. 0 is linear, -0.5 is like a 2:1
    compressor. This is where a regulator shows up.
  - Gain by input level (full band, in fifths of the file's block levels): the static curve of the dynamics.
  - Dynamics of the output: block level range (p95 - p10) and crest factor (peak - RMS).
A mic take's gain includes the speaker, the room and the mic, but those are the same in every take of the same
setup, so differences between columns are what matter. --blind writes level-matched copies of the takes under
random names for listening, and --csv writes the block gains for charts.

How: the coarse position comes from correlating the 10 ms level envelopes (dB) of the take and the file, which works
even when the chirps sit near a mic's noise floor; then each song excerpt is aligned to the sample by FFT cross-correlation of 0.68 s of music (search +-0.34 s), so a dropout or clock drift in one part does
not move the other. The correlation uses the sample-to-sample difference of both signals, which weights the treble:
a high-pass turns the bass phase around (a plain correlation then peaks negative and 1-2 ms late), the treble not. Band levels come from 4096-point Hann FFT frames (85 ms), summed into blocks (default 4 frames,
0.34 s). Blocks below -60 dBFS in the file, or less than 10 dB above the take's noise floor (measured before the
chirp), are left out. Pure Python, standard library only; a take takes about 20 s.
Why: pink noise showed the same spectrum on both systems, yet Windows sounds better with music, so the difference
must be in how the processing moves over time. These numbers show it instead of relying on memory.

The takes are copies of copyrighted music: keep them, the --blind files and the CSV in logs/ (gitignored).

Usage:
    python3 -I compare.py music-test.wav TAKE.wav [TAKE.wav ...] [--json FILE] [--frames 4] [--csv FILE]
                          [--blind DIR]
"""

import argparse
import array
import cmath
import json
import math
import operator
import random
import struct
import sys
from pathlib import Path

N = 4096          # FFT frame for band levels
TEMPLATE = 32768  # music used for alignment (0.68 s at 48 kHz)
BANDS = [("20-150", 20, 150), ("150-500", 150, 500), ("500-2k", 500, 2000), ("2k-5k", 2000, 5000),
         ("5k-10k", 5000, 10000), ("10k-20k", 10000, 20000), ("150-20k", 150, 20000)]
ALL_NOTE = "150 Hz - 20 kHz, the speakers' range: the bass below it would rule a full-band level"
ALL = len(BANDS) - 1
_fft_cache = {}


def read_wav(path):
    """(rate, channels, interleaved samples as floats in -1..1) of a 16/24/32-bit PCM or float32 WAV."""
    raw = Path(path).read_bytes()
    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        sys.exit(f"not a WAV file: {path}")
    pos, fmt, data = 12, None, None
    while pos + 8 <= len(raw):
        cid, size = raw[pos:pos + 4], struct.unpack("<I", raw[pos + 4:pos + 8])[0]
        if cid == b"fmt ":
            fmt = raw[pos + 8:pos + 8 + size]
        elif cid == b"data":
            data = raw[pos + 8:pos + 8 + size]
        pos += 8 + size + (size & 1)
    tag, ch, rate, _, _, bits = struct.unpack("<HHIIHH", fmt[:16])
    if tag == 0xFFFE:  # WAVE_FORMAT_EXTENSIBLE: the real tag starts the sub-format GUID
        tag = struct.unpack("<H", fmt[24:26])[0]
    if tag == 3 and bits == 32:
        f = array.array("f")
        f.frombytes(data[:len(data) // 4 * 4])
        x = array.array("d", f)
    elif tag == 1 and bits == 16:
        h = array.array("h")
        h.frombytes(data[:len(data) // 2 * 2])
        x = array.array("d", (v / 32768 for v in h))
    elif tag == 1 and bits in (24, 32):
        if bits == 24:  # put the 3 bytes in the top of an int32
            n = len(data) // 3
            b = bytearray(n * 4)
            b[1::4], b[2::4], b[3::4] = data[0:n * 3:3], data[1:n * 3:3], data[2:n * 3:3]
            data = bytes(b)
        i = array.array("i")
        i.frombytes(data[:len(data) // 4 * 4])
        x = array.array("d", (v / 2147483648 for v in i))
    else:
        sys.exit(f"unsupported WAV format (tag {tag}, {bits}-bit): {path}")
    return rate, ch, x[:len(x) // ch * ch]


def write_float_wav(path, rate, ch, samples):
    body = array.array("f", samples).tobytes()
    head = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(body), b"WAVE", b"fmt ", 16, 3, ch, rate,
                       rate * ch * 4, ch * 4, 32, b"data", len(body))
    Path(path).write_bytes(head + body)


def mono(x, ch):
    if ch == 1:
        return x
    m = array.array("d", x[0::ch])
    for c in range(1, ch):
        m = array.array("d", map(operator.add, m, x[c::ch]))
    return array.array("d", (v / ch for v in m))


def fft(a):
    """Iterative radix-2 FFT of a list of complex numbers (length a power of 2). Returns a new list."""
    n = len(a)
    if n not in _fft_cache:
        rev, j = [0] * n, 0
        for i in range(1, n):
            bit = n >> 1
            while j & bit:
                j ^= bit
                bit >>= 1
            j |= bit
            rev[i] = j
        _fft_cache[n] = (rev, [cmath.exp(-2j * math.pi * k / n) for k in range(n // 2)])
    rev, tw = _fft_cache[n]
    a = [a[i] for i in rev]
    size = 2
    while size <= n:
        half = size // 2
        ws = tw[::n // size]
        for start in range(0, n, size):
            for k in range(half):
                i = start + k
                t = ws[k] * a[i + half]
                u = a[i]
                a[i] = u + t
                a[i + half] = u - t
        size *= 2
    return a


def ifft(a):
    n = len(a)
    return [v.conjugate() / n for v in fft([v.conjugate() for v in a])]


def db(p):
    return 10 * math.log10(p) if p > 0 else -200.0


class BandMeter:
    """Band powers (RMS^2, like analyze.py) of one Hann-windowed N-point frame."""

    def __init__(self, rate):
        self.win = [0.5 - 0.5 * math.cos(2 * math.pi * i / N) for i in range(N)]
        self.scale = 2 / (sum(w * w for w in self.win) * N)
        self.bins = [(max(1, math.ceil(lo * N / rate)), min(N // 2, math.ceil(hi * N / rate))) for _, lo, hi in BANDS]

    def __call__(self, xs, start):
        frame = xs[max(0, start):start + N]
        if start < 0:
            frame = array.array("d", [0.0] * -start) + frame
        frame = list(frame) + [0.0] * (N - len(frame))
        spec = fft([complex(v * w) for v, w in zip(frame, self.win)])
        pw = [z.real * z.real + z.imag * z.imag for z in spec[:N // 2]]
        return [sum(pw[lo:hi]) * self.scale for lo, hi in self.bins]


def diff(m):
    return array.array("d", [0.0]) + array.array("d", map(operator.sub, m[1:], m))


def envelope(m, rate):
    """10 ms block levels in dB, floored 50 dB below the loudest block, mean removed."""
    n = rate // 100
    lv = [db(sum(map(operator.mul, m[i:i + n], m[i:i + n])) / n) for i in range(0, len(m) - n + 1, n)]
    top = max(lv)
    lv = [max(v, top - 50) for v in lv]
    mean = sum(lv) / len(lv)
    return [v - mean for v in lv]


def coarse(ref_env, m, rate):
    """Offset (take sample - file sample) to within 10 ms, from the envelope correlation."""
    env = envelope(m, rate)
    lags = range(-100, len(env) - len(ref_env) + 101)
    score = lambda k: sum(a * env[i + k] for i, a in enumerate(ref_env) if 0 <= i + k < len(env))
    return max(lags, key=score) * (rate // 100)


def noise_end(m, rate, off, parts):
    """End of the take's silence before the first chirp (sample index)."""
    return max(0, off + int((parts[0]["chirp_at"] - 0.05) * rate))


def align(ref_m, m, ref_pos, est):
    """Offset (take index - file index) of the music at ref_pos, searched +-TEMPLATE/2 around est, and its r."""
    t = list(ref_m[ref_pos:ref_pos + TEMPLATE])
    w0 = ref_pos + est - TEMPLATE // 2
    w = [m[i] if 0 <= i < len(m) else 0.0 for i in range(w0, w0 + 2 * TEMPLATE)]
    T = fft([complex(v) for v in t] + [0j] * TEMPLATE)
    W = fft([complex(v) for v in w])
    c = ifft([a.conjugate() * b for a, b in zip(T, W)])
    k = max(range(TEMPLATE + 1), key=lambda i: abs(c[i].real))  # a mic take may peak negative (room, polarity)
    energy = sum(v * v for v in t) * sum(v * v for v in w[k:k + TEMPLATE])
    r = c[k].real / math.sqrt(energy) if energy > 0 else 0.0
    return w0 + k - ref_pos, r


def pct(xs, p):
    s = sorted(xs)
    return s[min(len(s) - 1, int(p / 100 * len(s)))]


def slope(xs, ys):
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / vx if vx > 0 else 0.0


def frame_starts(part, rate):
    a = int((part["music_at"] + 0.1) * rate)
    b = int((part["music_at"] + part["seconds"] - 0.1) * rate)
    return list(range(a, b - N, N))


def blocks(frames, k):
    """Sum k consecutive frames of band powers into blocks, as dB."""
    return [[db(sum(f[b] for f in frames[i:i + k])) for b in range(len(BANDS))]
            for i in range(0, len(frames) - k + 1, k)]


def analyze(path, ref, args):
    rate, parts, meter = ref["rate"], ref["parts"], ref["meter"]
    trate, ch, x = read_wav(path)
    if trate != rate:
        sys.exit(f"{path}: {trate} Hz, the file is {rate} Hz")
    m = mono(x, ch)
    est = coarse(ref["env"], m, rate)
    offs, dm = [], diff(m)
    for p in parts:
        off, r = align(ref["diff"], dm, int((p["music_at"] + 1.0) * rate), est)
        offs.append((off, r))
        est = off
    noise_frames = [meter(m, s) for s in range(0, noise_end(m, rate, offs[0][0], parts) - N, N)]
    noise = [pct([db(f[b]) for f in noise_frames], 50) if noise_frames else -200.0 for b in range(len(BANDS))]

    rows = []  # (part, time in file, in dB per band, out dB per band)
    for pi, p in enumerate(parts):
        starts = frame_starts(p, rate)
        out = blocks([meter(m, s + offs[pi][0]) for s in starts], args.frames)
        for j, (i_db, o_db) in enumerate(zip(ref["blocks"][pi], out)):
            rows.append((pi + 1, starts[j * args.frames] / rate, i_db, o_db))

    res = {"path": path, "rate": rate, "ch": ch, "offs": offs, "noise": noise, "rows": rows,
           "med": [], "spread": [], "slope": [], "count": []}
    for b in range(len(BANDS)):
        ok = [(i[b], o[b] - i[b]) for _, _, i, o in rows if i[b] > -60 and i[ALL] > -50 and o[b] > noise[b] + 10]
        res["count"].append(len(ok))
        if len(ok) < 5:
            res["med"].append(None), res["spread"].append(None), res["slope"].append(None)
            continue
        g = [y for _, y in ok]
        res["med"].append(pct(g, 50))
        res["spread"].append(pct(g, 90) - pct(g, 10))
        res["slope"].append(slope([v for v, _ in ok], g))
    offset = res["med"][ALL]
    if offset is None:
        sys.exit(f"{path}: too few usable blocks (is it the right file, and loud enough?)")
    edges = [-200] + ref["edges"] + [200]
    res["by_level"] = []
    for lo, hi in zip(edges, edges[1:]):
        g = [o[ALL] - i[ALL] - offset for _, _, i, o in rows if lo <= i[ALL] < hi and o[ALL] > noise[ALL] + 10]
        res["by_level"].append(sum(g) / len(g) if len(g) >= 3 else None)
    lv = [o[ALL] for _, _, _, o in rows if o[ALL] > noise[ALL] + 10]
    res["range"] = pct(lv, 95) - pct(lv, 10)
    res["crest"] = crest(x, ch, parts, rate, [o for o, _ in offs])
    if args.blind:
        res["music"] = [x[max(0, (int(p["music_at"] * rate) + o) * ch):(int((p["music_at"] + p["seconds"]) * rate) + o) * ch]
                        for p, (o, _) in zip(parts, offs)]
    return res


def crest(x, ch, parts, rate, offs):
    peak, ss, n = 0.0, 0.0, 0
    for p, o in zip(parts, offs):
        seg = x[max(0, (int(p["music_at"] * rate) + o) * ch):(int((p["music_at"] + p["seconds"]) * rate) + o) * ch]
        if seg:
            peak = max(peak, max(map(abs, seg)))
            ss += sum(map(operator.mul, seg, seg))
            n += len(seg)
    return db(peak * peak) - db(ss / n) if n and peak > 0 else None


def fmt(v, sign=True, width=8):
    return f"{'-':>{width}}" if v is None else f"{v:>+{width}.1f}" if sign else f"{v:>{width}.1f}"


def table(title, label_rows, takes, sign=True):
    print(f"\n{title}")
    print(f"{'':<12}" + "".join(f"{f'[{i + 1}]':>8}" for i in range(len(takes))))
    for label, getter in label_rows:
        print(f"{label:<12}" + "".join(fmt(getter(t), sign) for t in takes))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ref", type=Path, help="music-test.wav")
    ap.add_argument("takes", type=Path, nargs="+")
    ap.add_argument("--json", type=Path, help="layout file (default: REF with .json)")
    ap.add_argument("--frames", type=int, default=4, help="85 ms frames per block (default 4 = 0.34 s)")
    ap.add_argument("--csv", type=Path, help="write the block levels of every take here")
    ap.add_argument("--blind", type=Path, help="write level-matched takes under random names here, key in key.txt")
    args = ap.parse_args()

    info = json.loads((args.json or args.ref.with_suffix(".json")).read_text())
    rate, ch, x = read_wav(args.ref)
    ref = {"rate": rate, "parts": info["parts"], "mono": mono(x, ch), "meter": BandMeter(rate)}
    ref["diff"] = diff(ref["mono"])
    ref["env"] = envelope(ref["mono"], rate)
    ref["blocks"] = [blocks([ref["meter"](ref["mono"], s) for s in frame_starts(p, rate)], args.frames)
                     for p in info["parts"]]
    ref_crest = crest(x, ch, info["parts"], rate, [0] * len(info["parts"]))
    lv = [b[ALL] for part in ref["blocks"] for b in part if b[ALL] > -60]
    ref_range = pct(lv, 95) - pct(lv, 10)
    ref["edges"] = [round(pct(lv, q) * 2) / 2 for q in (20, 40, 60, 80)]  # fifths of the file's block levels
    del x

    takes = []
    for i, path in enumerate(args.takes):
        print(f"[{i + 1}] analyzing {path.name} ...", file=sys.stderr, flush=True)
        takes.append(analyze(path, ref, args))

    print(f"{args.ref.name}: {len(info['parts'])} parts, blocks of {args.frames * N / rate:.2f} s")
    for i, t in enumerate(takes):
        (o1, r1), *rest = t["offs"]
        line = f"[{i + 1}] {t['path'].name}  {t['ch']} ch  offset {o1 / rate:+.4f} s (r {r1:.3f})"
        for (o, r), p0, p in zip(rest, info["parts"], info["parts"][1:]):
            line += f", part 2 {o / rate:+.4f} s (r {r:.3f}, drift {(o - o1) / ((p['music_at'] - p0['music_at']) * rate) * 1e6:+.0f} ppm)"
        print(line)
        span = (info["parts"][-1]["music_at"] - info["parts"][0]["music_at"]) * rate
        if min(abs(r) for _, r in t["offs"]) < 0.3 or abs(t["offs"][-1][0] - o1) / span > 500e-6:
            print("    check: low |r| or the parts disagree, so the alignment may be wrong")

    table(f"Level: median full-band gain ({ALL_NOTE}), take - file (dB)."
          " The tables below are relative to it (level-matched).",
          [(f"{BANDS[ALL][0]} Hz", lambda t: t["med"][ALL])], takes)
    rel = lambda b: lambda t: None if t["med"][b] is None else t["med"][b] - t["med"][ALL]
    table("Spectrum: median gain per band, relative to the full band (dB)",
          [(f"{n} Hz", rel(b)) for b, (n, _, _) in enumerate(BANDS[:ALL])], takes)
    table("Movement: p90 - p10 of the block gain (dB). 0 = fixed EQ, more = it reacts to the music",
          [(f"{n} Hz", (lambda b: lambda t: t["spread"][b])(b)) for b, (n, _, _) in enumerate(BANDS)],
          takes, sign=False)
    table("Slope: block gain vs block input level in the band (dB/dB). 0 = linear, -0.5 = like 2:1",
          [(f"{n} Hz", (lambda b: lambda t: t["slope"][b])(b)) for b, (n, _, _) in enumerate(BANDS)],
          takes)
    edges = ref["edges"]
    labels = [f"< {edges[0]}"] + [f"{a}..{b}" for a, b in zip(edges, edges[1:])] + [f">= {edges[-1]}"]
    table("Gain by full-band input level (dBFS of the file block, fifths), relative to the take's median (dB)",
          [(lab, (lambda j: lambda t: t["by_level"][j])(j)) for j, lab in enumerate(labels)], takes)
    table(f"Dynamics of the output (file: range {ref_range:.1f} dB, crest {ref_crest:.1f} dB)",
          [("range", lambda t: t["range"]), ("crest", lambda t: t["crest"])], takes, sign=False)
    low = [f"[{i + 1}] {BANDS[b][0]} Hz ({t['count'][b]} blocks)" for i, t in enumerate(takes)
           for b in range(len(BANDS)) if t["count"][b] < 20]
    if low:
        print("\nFew usable blocks (near the noise floor): " + ", ".join(low))

    if args.csv:
        with open(args.csv, "w") as f:
            f.write("take,file,part,t_s,band,in_db,out_db,gain_db\n")
            for i, t in enumerate(takes):
                for part, ts, i_db, o_db in t["rows"]:
                    for b, (n, _, _) in enumerate(BANDS):
                        f.write(f"{i + 1},{t['path'].name},{part},{ts:.3f},{n},{i_db[b]:.2f},{o_db[b]:.2f},"
                                f"{o_db[b] - i_db[b]:.2f}\n")
        print(f"\nBlock levels written to {args.csv}")

    if args.blind:
        args.blind.mkdir(parents=True, exist_ok=True)
        names = random.SystemRandom().sample([chr(ord("A") + i) for i in range(26)], len(takes))
        key = []
        for name, t in zip(names, takes):
            g = 10 ** ((takes[0]["med"][ALL] - t["med"][ALL]) / 20)
            gap = array.array("d", [0.0] * (rate // 2 * t["ch"]))
            out = array.array("d")
            for seg in t["music"]:
                out += array.array("d", (v * g for v in seg)) + gap
            write_float_wav(args.blind / f"{name}.wav", rate, t["ch"], out)
            key.append(f"{name}.wav = {t['path'].name} (gain {20 * math.log10(g):+.1f} dB)")
        (args.blind / "key.txt").write_text("\n".join(sorted(key)) + "\n")
        print(f"\nBlind files in {args.blind}: {', '.join(sorted(n + '.wav' for n in names))}. "
              "Listen before opening key.txt.")


if __name__ == "__main__":
    main()
