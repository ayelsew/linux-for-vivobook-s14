#!/usr/bin/env bash
# Author: @ayelsew
# https://github.com/ayelsew/linux-for-vivobook-s14
#
# play-loop.sh: play an audio file in a loop, for A/B tests of EasyEffects presets. It plays through the default
# output, so through EasyEffects when it is running.
#
# Usage: sound/play-loop.sh FILE [START END]
#   FILE        a path, or a name recorded by record-loop.sh (looked up in logs/sound-loops/, .wav optional)
#   START END   optional: loop only this part, in seconds or mm:ss (e.g. 0:42 0:58)
# Keys in mpv: space pause, l set/clear an A-B loop by hand, q quit.

set -euo pipefail

[[ $# -eq 1 || $# -eq 3 ]] || { sed -n '8,11p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

file="$1"
if [[ ! -f "$file" ]]; then
    dir="$(cd "$(dirname "$0")/.." && pwd)/logs/sound-loops"
    for try in "$dir/$file" "$dir/$file.wav"; do
        [[ -f "$try" ]] && { file="$try"; break; }
    done
fi
[[ -f "$file" ]] || { echo "File not found: $1" >&2; exit 1; }

args=(--no-video --loop-file=inf)
if [[ $# -eq 3 ]]; then
    args+=(--start="$2" --ab-loop-a="$2" --ab-loop-b="$3")
fi

echo "Looping: $file   (q to quit)"
exec mpv "${args[@]}" "$file"
