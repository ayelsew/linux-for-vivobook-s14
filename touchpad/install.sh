#!/bin/sh
# Download the touchpad edge gestures from GitHub and run the installer (gtouchpad.sh install).
# Author: @ayelsew
# https://github.com/ayelsew/linux-for-vivobook-s14
#
#   curl -fsSL https://raw.githubusercontent.com/ayelsew/linux-for-vivobook-s14/refs/heads/main/touchpad/install.sh | sh

# Everything runs inside main, so nothing starts until the whole script has been downloaded.
main() {
    set -eu

    repo="ayelsew/linux-for-vivobook-s14"
    branch="main"
    url="https://github.com/$repo/archive/refs/heads/$branch.tar.gz"

    for c in curl tar bash mktemp; do
        command -v "$c" >/dev/null 2>&1 || { echo "Missing command: $c" >&2; exit 1; }
    done

    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT

    echo ":: Downloading $repo ($branch)"
    curl -fsSL "$url" | tar -xz -C "$tmp"

    installer="$tmp/linux-for-vivobook-s14-$branch/touchpad/install/gtouchpad.sh"
    [ -f "$installer" ] || { echo "Installer not found in the download" >&2; exit 1; }

    # With "curl | sh" the keyboard is not the input: give the installer the terminal back,
    # so it can ask questions and sudo can ask for the password.
    if (exec </dev/tty) 2>/dev/null; then
        bash "$installer" install </dev/tty
    else
        bash "$installer" install
    fi
}

main "$@"
