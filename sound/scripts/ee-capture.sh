#!/usr/bin/env bash
# Author: @ayelsew
# https://github.com/ayelsew/linux-for-vivobook-s14
#
# ee-capture.sh: digital capture of EasyEffects' OUTPUT while it plays music-test.wav, once per preset.
#
# What: for each preset it loads the preset, plays the file into easyeffects_sink and records the monitor of the
# speaker sink, which is the signal after every effect, before the codec. It is the Linux side of the Windows
# loopback captures (logs/music-test/null-win-loopback-*.wav), so compare.py can compare EasyEffects and Dolby sample
# by sample, with no mic or room in between.
# How: pw-record on the speaker sink with stream.capture.sink, float32 stereo 48 kHz. The monitor is taken before the
# hardware volume (the KDE slider is the codec gain), like the Windows loopback. The music is audible while it runs.
# The preset that was loaded before is loaded again at the end.
#
# Usage: sound/measure/ee-capture.sh [PRESET...]
#   default presets: Flat S5406SA-Dolby-music S5406SA-Dolby-dynamic
#   SINK=...  speaker sink to record (default: the sink whose name contains "Speaker")
# Output: logs/music-test/linux-ee-out-PRESET.wav. Check the Flat one with:
#   python3 -I sound/measure/musictest.py null logs/music-test/music-test.wav logs/music-test/linux-ee-out-Flat.wav

set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
dir="$root/logs/music-test"
file="$dir/music-test.wav"
[[ -f "$file" ]] || { echo "Missing $file (build it with musictest.py build)." >&2; exit 1; }
pactl list short sinks | awk '{print $2}' | grep -qx easyeffects_sink \
    || { echo "EasyEffects is not running. Start it (easyeffects --service-mode -w &) and try again." >&2; exit 1; }
sink="${SINK:-$(pactl list short sinks | awk '$2 ~ /Speaker/ {print $2; exit}')}"
[[ -n "$sink" ]] || { echo "No speaker sink found: set SINK=..." >&2; exit 1; }

presets=("$@")
[[ ${#presets[@]} -gt 0 ]] || presets=(Flat S5406SA-Dolby-music S5406SA-Dolby-dynamic)
before="$(easyeffects -a output 2>/dev/null || true)"
secs="$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["length_s"])' "$dir/music-test.json")"

echo "Recording the monitor of $sink"
for p in "${presets[@]}"; do
    out="$dir/linux-ee-out-$p.wav"
    easyeffects -l "$p"
    sleep 2  # let the new pipeline settle
    pw-record --target "$sink" -P '{ stream.capture.sink = true }' \
        --rate 48000 --channels 2 --format f32 "$out" &
    rec=$!
    sleep 1
    echo "  $p: playing $secs s..."
    pw-play --target easyeffects_sink "$file"
    sleep 1
    kill -INT "$rec"  # SIGINT lets pw-record close the WAV file properly
    wait "$rec" || true
    echo "  saved $out"
done

if [[ -n "$before" ]]; then easyeffects -l "$before" && echo "Loaded $before again."; fi
