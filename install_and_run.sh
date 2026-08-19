#!/usr/bin/env bash
# Nozomi Guardian Zone Import Tool - macOS / Linux launcher
# Creates an isolated virtual environment, installs this package and its
# dependencies into it automatically, then launches the GUI.
set -e
cd "$(dirname "$0")"

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Python 3 was not found on this system."
    echo "Install it first:"
    echo "  macOS:   brew install python3   (or https://www.python.org/downloads/)"
    echo "  Debian/Ubuntu: sudo apt-get install python3 python3-venv python3-tk python3-pip"
    echo "  Fedora:  sudo dnf install python3 python3-tkinter"
    exit 1
fi

VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[setup] Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR" || {
        echo "[setup] venv module unavailable, continuing with system Python instead.";
        VENV_DIR="";
    }
fi

if [ -n "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/python" ]; then
    RUN_PY="$VENV_DIR/bin/python"
else
    RUN_PY="$PYTHON"
fi

echo "[setup] Installing/upgrading the tool and its dependencies..."
"$RUN_PY" -m pip install --quiet --upgrade pip || true
"$RUN_PY" -m pip install --quiet -e . || \
    "$RUN_PY" -m pip install --quiet --break-system-packages -e .

echo "[setup] Launching Nozomi Guardian Zone Import Tool..."
"$RUN_PY" -m nozomi_zone_import_tool
