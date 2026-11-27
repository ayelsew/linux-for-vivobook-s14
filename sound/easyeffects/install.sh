#!/usr/bin/env bash
# Author: @ayelsew
# https://github.com/ayelsew/linux-for-vivobook-s14
#
# install.sh: set up the Dolby-based EasyEffects presets for the current user on the ASUS Vivobook S14 S5406SA.
#
# What it does (all inside your home, no sudo):
#   1. Copies presets/*.json to ~/.local/share/easyeffects/output/. A preset with the same name that differs is kept
#      as NAME.json.bak-DATE first.
#   2. Autoloads one preset on the laptop speakers only (EasyEffects -> Presets -> Autoload). Headphones, Bluetooth
#      and USB DACs stay untouched, because the Dolby tuning is for these speakers.
#   3. Starts EasyEffects at login, in service mode with no window (the same entry EasyEffects' own
#      "Autostart on login" switch writes), and starts it now if it is not running.
# EasyEffects keeps everything per user, so every account that wants the presets runs this once, logged in as itself.
#
# Usage:
#   ./install.sh [install] [--preset NAME]   default preset: S5406SA-Dolby-music-v2
#   ./install.sh uninstall                   removes what install added (presets, autoload, autostart)
#   ./install.sh status

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
data="${XDG_DATA_HOME:-$HOME/.local/share}/easyeffects"
config="${XDG_CONFIG_HOME:-$HOME/.config}"
presets_dir="$data/output"
autoload_dir="$data/autoload/output"
autostart="$config/autostart/com.github.wwmm.easyeffects.desktop"
state="$data/.s5406sa-install"   # what install added, for uninstall

# The speakers' PipeWire sink and route on this laptop. Read from the live session when possible.
sink_default="alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__Speaker__sink"
desc_default="Core Ultra 200V Series Processors HD Audio Speaker"
route="Speaker"   # EasyEffects matches the route description, and names the file "<sink>:<route>.json"

preset="S5406SA-Dolby-music-v2"

die() { echo "Error: $*" >&2; exit 1; }

find_sink() {
    sink="" desc=""
    if command -v pactl >/dev/null 2>&1 && pactl info >/dev/null 2>&1; then
        sink="$(pactl list short sinks | awk '$2 ~ /HiFi__Speaker__sink$/ {print $2; exit}')"
        [[ -n "$sink" ]] && desc="$(pactl list sinks | awk -v s="$sink" '
            $1 == "Name:" {cur = $2} cur == s && $1 == "Description:" {sub(/^[ \t]*Description: /, ""); print; exit}')"
    fi
    if [[ -z "$sink" ]]; then
        echo ":: No audio session found, using the known speaker name of this laptop"
        sink="$sink_default"
    fi
    desc="${desc:-$desc_default}"
}

do_install() {
    command -v easyeffects >/dev/null 2>&1 || die "easyeffects is not installed: sudo pacman -S easyeffects lsp-plugins-lv2"
    [[ -d /usr/lib/lv2/lsp-plugins.lv2 ]] \
        || die "lsp-plugins-lv2 is not installed (without it the plugins do nothing): sudo pacman -S lsp-plugins-lv2"
    [[ -f "$here/presets/$preset.json" ]] || die "no preset $preset in $here/presets"

    mkdir -p "$presets_dir" "$autoload_dir" "$(dirname "$autostart")"
    : > "$state.new"

    echo ":: Presets -> $presets_dir"
    for f in "$here"/presets/*.json; do
        name="$(basename "$f")"
        dest="$presets_dir/$name"
        if [[ -f "$dest" ]] && ! cmp -s "$f" "$dest"; then
            mv "$dest" "$dest.bak-$(date +%Y%m%d-%H%M%S)"
            echo "   $name: your old copy was different, kept as .bak"
        fi
        cp "$f" "$dest"
        echo "preset $dest" >> "$state.new"
    done

    find_sink
    file="$autoload_dir/${sink//\//_}:${route//\//_}.json"
    echo ":: Autoload $preset on \"$desc\""
    printf '{\n    "device": "%s",\n    "device-description": "%s",\n    "device-profile": "%s",\n    "preset-name": "%s"\n}\n' \
        "$sink" "$desc" "$route" "$preset" > "$file"
    echo "autoload $file" >> "$state.new"

    if [[ ! -f "$autostart" ]]; then
        echo ":: Autostart at login -> $autostart"
        cat > "$autostart" <<'EOF'
[Desktop Entry]
Name=Easy Effects
Comment=Easy Effects Service
Exec=easyeffects --hide-window --service-mode
Icon=com.github.wwmm.easyeffects
StartupNotify=false
Terminal=false
Type=Application
X-GNOME-Autostart-Phase=Application
X-KDE-autostart-phase=2
EOF
        echo "autostart $autostart" >> "$state.new"
    else
        echo ":: Autostart already set up, left as it is"
    fi
    # Keep EasyEffects' own "Autostart on login" switch in step with the file.
    if command -v kwriteconfig6 >/dev/null 2>&1; then
        kwriteconfig6 --file "$config/easyeffects/db/easyeffectsrc" --group Window --key autostartOnLogin true
    fi

    # Merge with an earlier install, so uninstall still knows about everything.
    [[ -f "$state" ]] && cat "$state" >> "$state.new"
    sort -u "$state.new" > "$state" && rm -f "$state.new"

    if pgrep -u "$(id -u)" -x easyeffects >/dev/null 2>&1; then
        easyeffects -l "$preset" >/dev/null 2>&1 && echo ":: EasyEffects is running: loaded $preset"
    elif [[ -n "${WAYLAND_DISPLAY:-}${DISPLAY:-}" ]]; then
        setsid easyeffects --hide-window --service-mode >/dev/null 2>&1 < /dev/null &
        echo ":: Started EasyEffects"
    else
        echo ":: Not in a desktop session: EasyEffects starts at your next login"
    fi
    echo "Done. Change the speaker preset any time in EasyEffects -> Presets -> Autoload."
}

do_uninstall() {
    [[ -f "$state" ]] || die "nothing to remove (no $state)"
    while read -r kind path; do
        [[ -e "$path" ]] || continue
        rm -f "$path"
        echo "removed $kind $path"
        if [[ "$kind" == autostart ]] && command -v kwriteconfig6 >/dev/null 2>&1; then
            kwriteconfig6 --file "$config/easyeffects/db/easyeffectsrc" --group Window --key autostartOnLogin false
        fi
    done < "$state"
    rm -f "$state"
    echo "Done. EasyEffects itself stays installed; restart it (easyeffects -q) to drop the loaded preset."
}

do_status() {
    find_sink
    file="$autoload_dir/${sink//\//_}:${route//\//_}.json"
    echo "Speaker sink: $sink"
    if [[ -f "$file" ]]; then
        echo "Autoload:     $(sed -n 's/.*"preset-name": "\(.*\)".*/\1/p' "$file")"
    else
        echo "Autoload:     none"
    fi
    [[ -f "$autostart" ]] && echo "Autostart:    yes" || echo "Autostart:    no"
    pgrep -u "$(id -u)" -x easyeffects >/dev/null 2>&1 \
        && echo "Running:      yes, preset $(easyeffects -a output 2>/dev/null)" || echo "Running:      no"
}

cmd="install"
while [[ $# -gt 0 ]]; do
    case "$1" in
        install|uninstall|status) cmd="$1" ;;
        --preset) preset="${2:?--preset needs a name}"; shift ;;
        -h|--help) sed -n '5,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) die "unknown argument: $1 (see --help)" ;;
    esac
    shift
done

"do_$cmd"
