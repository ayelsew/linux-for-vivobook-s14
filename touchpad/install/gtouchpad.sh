#!/usr/bin/env bash
# gtouchpad — install and control the touchpad edge-gestures daemon (ASUS Vivobook S 14 S5406SA).
# Author: @ayelsew
# https://github.com/ayelsew/linux-for-vivobook-s14
#
# Run as your normal user, NOT with sudo. sudo is asked only for the udev rule.

set -euo pipefail

NAME="touchpad-edge-gestures"
CMD="gtouchpad"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOUCHPAD_NAME="ASCP1200:00 093A:3016 Touchpad"

BIN_DIR="$HOME/.local/bin"
LIB_DIR="$HOME/.local/lib/$NAME"
UNIT_DIR="$HOME/.config/systemd/user"
RULE_DIR="/etc/udev/rules.d"
CONF="$HOME/.config/gtouchpad.conf"
REPO_URL="https://github.com/ayelsew/linux-for-vivobook-s14"
# One file per desktop: desktops/<name>_ctl.py (contract in desktops/README.md)
DESKTOPS_SRC="$SRC_DIR/desktops"

PY="$NAME.py"
UNIT="$NAME.service"
RULE="70-$NAME.rules"

info() { printf '\033[1;34m::\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m✓\033[0m  %s\n' "$*"; }
warn() { printf '\033[1;33m!\033[0m  %s\n' "$*" >&2; }
die()  { printf '\033[1;31m✗\033[0m  %s\n' "$*" >&2; exit 1; }

usage() {
    cat <<'EOF'
gtouchpad — touchpad edge gestures (volume, brightness, media, corner)

Usage:
  ./gtouchpad.sh install   install or update (run from the repo's install/ folder)
  gtouchpad on             turn the gestures on (also after reboot)
  gtouchpad off            turn the gestures off (also after reboot)
  gtouchpad status         show if the gestures are on and running
  gtouchpad corner         change the program opened by the top-right corner gesture
  gtouchpad corner "CMD"   set it directly (example: gtouchpad corner systemsettings)
  gtouchpad corner ""      no program (the corner gesture does nothing)
  gtouchpad uninstall      remove everything, including gtouchpad itself

It installs:
  ~/.local/bin/gtouchpad                              this command
  ~/.local/lib/touchpad-edge-gestures/                the daemon and desktops/*_ctl.py
  ~/.config/systemd/user/touchpad-edge-gestures.service
  /etc/udev/rules.d/70-touchpad-edge-gestures.rules   read access to the touchpad only (sudo)
  ~/.config/gtouchpad.conf                            your settings (corner program)
EOF
}

find_touchpad() {
    local p
    for p in /sys/class/input/event*; do
        if [[ -r "$p/device/name" && "$(<"$p/device/name")" == "$TOUCHPAD_NAME" ]]; then
            echo "/dev/input/${p##*/}"
            return 0
        fi
    done
    return 1
}

reload_udev() {
    sudo udevadm control --reload-rules
    sudo udevadm trigger --action=change --subsystem-match=input
    sudo udevadm settle --timeout=10 || true
}

# --- desktop integrations (desktops/*_ctl.py) -------------------------------

ctl_desktop()  { sed -n 's/^DESKTOP = "\(.*\)"$/\1/p' "$1"; }
ctl_requires() { sed -n 's/^REQUIRES = \[\(.*\)\]$/\1/p' "$1" | tr -d '",'; }

# Prints the *_ctl.py file whose DESKTOP is in XDG_CURRENT_DESKTOP, or nothing.
find_desktop_ctl() {
    local f d parts
    IFS=':' read -ra parts <<<"${XDG_CURRENT_DESKTOP:-}"
    for f in "$DESKTOPS_SRC"/*_ctl.py; do
        [[ -f "$f" ]] || continue
        for d in "${parts[@]}"; do
            [[ -n "$d" && "${d^^}" == "$(ctl_desktop "$f" | tr '[:lower:]' '[:upper:]')" ]] && { echo "$f"; return 0; }
        done
    done
}

# Prints the *_ctl.py file with FALLBACK = True.
find_fallback_ctl() {
    local f
    for f in "$DESKTOPS_SRC"/*_ctl.py; do
        grep -q '^FALLBACK = True' "$f" 2>/dev/null && { echo "$f"; return 0; }
    done
}

require_installed() {
    [[ -f "$UNIT_DIR/$UNIT" ]] || die "Not installed. Run ./gtouchpad.sh install from the repo's install/ folder."
}

# --- corner program (~/.config/gtouchpad.conf) -------------------------------

get_corner() {
    [[ -f "$CONF" ]] || return 0
    sed -n 's/^CORNER_PROGRAM="\(.*\)"$/\1/p' "$CONF"
}

# Checks the program and prints it with a full path (the service has a short PATH).
# Prints nothing for an empty value. Returns 1 if the program is not found or the value is invalid.
resolve_corner() {
    local value="$1" first rest path
    [[ -z "${value//[[:space:]]/}" ]] && return 0
    if [[ "$value" == *[\"\\\$\`]* ]]; then
        warn "Do not use quotes, backslashes, \$ or backticks"
        return 1
    fi
    read -r first rest <<<"$value"
    path="$(command -v -- "$first" 2>/dev/null || true)"
    if [[ -z "$path" || ! -x "$path" ]]; then
        warn "Program not found: $first"
        return 1
    fi
    echo "$path${rest:+ $rest}"
}

save_corner() {
    mkdir -p "$(dirname "$CONF")"
    printf '# gtouchpad settings (change with: gtouchpad corner)\nCORNER_PROGRAM="%s"\n' "$1" >"$CONF"
    if [[ -n "$1" ]]; then ok "Corner gesture opens: $1"; else ok "Corner gesture: no program"; fi
}

# Asks for the program; the current value comes pre-filled. Empty answer = no program.
ask_corner() {
    local current answer resolved
    current="$(get_corner)"
    echo
    echo "Top-right corner gesture (slide from the corner to the center), like MyASUS on Windows."
    echo "Program to open, with arguments if needed. Leave blank for no program. Examples:"
    echo "  systemsettings"
    echo "  systemsettings kcm_powerdevilprofilesconfig   (power profiles)"
    while true; do
        read -r -e -p "Program: " -i "$current" answer || answer=""
        if resolved="$(resolve_corner "$answer")"; then
            save_corner "$resolved"
            return 0
        fi
        current="$answer"
    done
}

cmd_corner() {
    require_installed
    if [[ $# -gt 0 ]]; then
        local resolved
        resolved="$(resolve_corner "$1")" || die "Corner program not changed"
        save_corner "$resolved"
    elif [[ -t 0 ]]; then
        ask_corner
    else
        local current; current="$(get_corner)"
        echo "Corner program: ${current:-(none)}"
        return 0
    fi
    if systemctl --user is-active --quiet "$UNIT"; then
        systemctl --user restart "$UNIT"
        ok "Service restarted with the new setting"
    fi
}

# --- on / off / status ------------------------------------------------------

cmd_on() {
    require_installed
    systemctl --user enable --now "$UNIT" >/dev/null 2>&1
    sleep 1
    if systemctl --user is-active --quiet "$UNIT"; then
        ok "Edge gestures ON"
    else
        die "Service did not start. Check: journalctl --user -u $NAME -e"
    fi
}

cmd_off() {
    require_installed
    systemctl --user disable --now "$UNIT" >/dev/null 2>&1
    ok "Edge gestures OFF"
}

cmd_status() {
    require_installed
    local enabled active
    enabled="$(systemctl --user is-enabled "$UNIT" 2>/dev/null || true)"
    active="$(systemctl --user is-active "$UNIT" 2>/dev/null || true)"
    if [[ "$active" == "active" ]]; then
        ok "Edge gestures ON (running, $enabled)"
    else
        warn "Edge gestures OFF ($active, $enabled)"
    fi
    local corner; corner="$(get_corner)"
    echo "Corner program: ${corner:-(none)}"
    echo "Logs: journalctl --user -u $NAME -f"
}

# --- install / uninstall ----------------------------------------------------

cmd_install() {
    for f in "$PY" "$UNIT" "$RULE"; do
        [[ -f "$SRC_DIR/$f" ]] || die "Missing $SRC_DIR/$f. Run install from the repo's install/ folder."
    done
    compgen -G "$DESKTOPS_SRC/*_ctl.py" >/dev/null || die "Missing $DESKTOPS_SRC/*_ctl.py"
    for c in python3 systemctl udevadm sudo; do
        command -v "$c" >/dev/null || die "Command not found: $c"
    done
    systemctl --user show-environment >/dev/null 2>&1 \
        || die "No systemd user session. Run this from your desktop session."

    local tp
    tp="$(find_touchpad)" || die "Touchpad \"$TOUCHPAD_NAME\" not found. Is this an S5406SA?"
    ok "Touchpad found: $tp"

    # Desktop: the daemon uses each desktop's own way to change volume/brightness/media.
    local ctl
    ctl="$(find_desktop_ctl)"
    if [[ -n "$ctl" ]]; then
        ok "Desktop: $(ctl_desktop "$ctl") (supported, desktops/${ctl##*/})"
    else
        ctl="$(find_fallback_ctl)"
        [[ -n "$ctl" ]] || die "No desktop integration with FALLBACK = True in $DESKTOPS_SRC"
        warn "Desktop \"${XDG_CURRENT_DESKTOP:-unknown}\" is not supported yet. The gestures will use the"
        warn "$(ctl_desktop "$ctl") commands ($(ctl_requires "$ctl")): they may work without the on-screen popup."
        warn "Help add it (see install/desktops/README.md): open a PR at $REPO_URL"
    fi
    # Commands the daemon calls for its actions (missing = that gesture does nothing).
    for c in $(ctl_requires "$ctl"); do
        command -v "$c" >/dev/null || warn "$c not installed: the gesture that uses it will not work"
    done

    # User files
    info "Installing the daemon, the user service and the $CMD command"
    install -Dm755 "$SRC_DIR/$PY"   "$LIB_DIR/$PY"
    rm -f "$LIB_DIR"/desktops/*_ctl.py   # so integrations removed from the repo don't stay behind
    install -d "$LIB_DIR/desktops"
    install -m644 "$DESKTOPS_SRC"/*_ctl.py "$LIB_DIR/desktops/"
    install -Dm644 "$SRC_DIR/$UNIT" "$UNIT_DIR/$UNIT"
    install -Dm755 "$SRC_DIR/gtouchpad.sh" "$BIN_DIR/$CMD"
    rm -f "$BIN_DIR/$PY"                 # old location (before desktops/ existed)
    ok "$LIB_DIR/$PY"
    ok "$LIB_DIR/desktops/ ($(cd "$LIB_DIR/desktops" && echo *_ctl.py))"
    ok "$UNIT_DIR/$UNIT"
    ok "$BIN_DIR/$CMD"
    case ":$PATH:" in
        *":$BIN_DIR:"*) ;;
        *) warn "$BIN_DIR is not in your PATH: add it to call '$CMD' from anywhere" ;;
    esac

    # udev rule (root)
    if cmp -s "$SRC_DIR/$RULE" "$RULE_DIR/$RULE"; then
        ok "udev rule already up to date: $RULE_DIR/$RULE"
    else
        info "Installing the udev rule (needs sudo)"
        sudo install -Dm644 "$SRC_DIR/$RULE" "$RULE_DIR/$RULE"
        reload_udev
        ok "$RULE_DIR/$RULE"
    fi

    # logind grants the access right after the udev change: wait a moment for it.
    local i
    for i in {1..10}; do
        [[ -r "$tp" ]] && break
        sleep 0.5
    done
    if [[ -r "$tp" ]]; then
        ok "Read access to $tp"
    else
        warn "Still no read access to $tp. Log out and back in, then run: $CMD on"
    fi

    # Corner program: ask now (pre-filled with the current value on updates)
    if [[ -t 0 ]]; then
        ask_corner
    elif [[ ! -f "$CONF" ]]; then
        save_corner ""
        echo "   Set it later with: $CMD corner"
    fi

    # Start
    systemctl --user daemon-reload
    systemctl --user enable "$UNIT" >/dev/null 2>&1
    systemctl --user restart "$UNIT"
    sleep 1
    if systemctl --user is-active --quiet "$UNIT"; then
        ok "Edge gestures ON"
    else
        warn "Service is not running. Check: journalctl --user -u $NAME -e"
        exit 1
    fi

    echo
    echo "From now on:  $CMD on | $CMD off | $CMD status | $CMD corner | $CMD uninstall"
}

cmd_uninstall() {
    info "Stopping and disabling the service"
    systemctl --user disable --now "$UNIT" >/dev/null 2>&1 || true
    rm -f "$UNIT_DIR/$UNIT" "$BIN_DIR/$PY" "$CONF"
    rm -rf "$LIB_DIR"
    systemctl --user daemon-reload
    ok "Removed $UNIT_DIR/$UNIT, $LIB_DIR and $CONF"

    if [[ -e "$RULE_DIR/$RULE" ]]; then
        info "Removing the udev rule (needs sudo)"
        sudo rm -f "$RULE_DIR/$RULE"
        reload_udev
        ok "Removed $RULE_DIR/$RULE"
    fi

    # Last: remove this command itself (bash keeps the file open, so deleting it is safe).
    rm -f "$BIN_DIR/$CMD"
    ok "Removed $BIN_DIR/$CMD"
    ok "Uninstalled"
}

# --- main -------------------------------------------------------------------

[[ $EUID -ne 0 ]] || die "Run as your normal user, not root (sudo is asked only when needed)."

case "${1:-}" in
    install)          cmd_install ;;
    uninstall)        cmd_uninstall ;;
    on)               cmd_on ;;
    off)              cmd_off ;;
    status)           cmd_status ;;
    corner)           shift; cmd_corner "$@" ;;
    ""|-h|--help|help) usage ;;
    *)                die "Unknown command: $1 (use --help)" ;;
esac
