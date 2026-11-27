#!/usr/bin/env bash
# Author: @ayelsew
# https://github.com/ayelsew/linux-for-vivobook-s14
#
# record-loop.sh: record a few seconds of what is playing, to loop it later for A/B tests of EasyEffects presets
# (for example the high-pass on the speakers).
#
# It records EasyEffects' input (easyeffects_sink), so the file is the music BEFORE any effect. Playing it back goes
# through EasyEffects again, once, like the original. If EasyEffects isn't running, it records the default output.
#
# Recordings go to logs/sound-loops/ (gitignored). They are copies of copyrighted music: keep them local.
#
# Usage: sound/record-loop.sh [-p] [SECONDS] [NAME]
#   SECONDS  length, default 20
#   NAME     file name without .wav, default loop-YYYYMMDD-HHMMSS
#   -p       loop the file with mpv right after recording (q to quit)
# Steps: pause the music at the start of the part you want, run the script, press play during the countdown.

set -euo pipefail

play=0
if [[ "${1:-}" == "-p" ]]; then play=1; shift; fi
secs="${1:-20}"
name="${2:-loop-$(date +%Y%m%d-%H%M%S)}"
[[ "$secs" =~ ^[0-9]+$ && "$secs" -gt 0 ]] || { echo "SECONDS must be a positive whole number" >&2; exit 1; }

dir="$(cd "$(dirname "$0")/.." && pwd)/logs/sound-loops"
mkdir -p "$dir"
out="$dir/$name.wav"

if pactl list short sinks | awk '{print $2}' | grep -qx easyeffects_sink; then
    sink=easyeffects_sink
    echo "Recording EasyEffects' input (before effects)."
else
    sink="$(pactl get-default-sink)"
    echo "EasyEffects is not running: recording the default output ($sink)."
fi

for n in 3 2 1; do printf '\rPress play now... %s ' "$n"; sleep 1; done
printf '\rRecording %s s...          \n' "$secs"
# SIGINT lets pw-record close the WAV file properly.
timeout --signal=INT "$secs" pw-record --target "$sink" -P '{ stream.capture.sink = true }' \
    --rate 48000 --channels 2 --format s24 "$out" || true

[[ -s "$out" ]] || { echo "Nothing was recorded." >&2; exit 1; }
echo "Saved: $out"
echo "Loop it (pause the music first): mpv --loop-file=inf \"$out\""

if [[ "$play" == 1 ]]; then
    echo "Pause the music player now. Looping in 3 s, q to quit."
    sleep 3
    mpv --no-video --loop-file=inf "$out"
fi
