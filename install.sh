#!/usr/bin/env sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
    echo 'Install Python 3.9+ and add it to PATH, then retry.' >&2
    exit 1
fi
exec python3 "$root/install/install.py" "$@"
