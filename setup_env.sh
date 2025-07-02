#!/usr/bin/env bash
# Simple helper script to create a Python virtual environment
# and install project dependencies.
set -e

OFFLINE=0
if [[ "$1" == "--offline" ]]; then
    OFFLINE=1
fi

if [ -d "venv" ]; then
    echo "Virtual environment already exists at ./venv" >&2
else
    python3 -m venv venv
    echo "Created virtual environment in ./venv" >&2
fi

# Activate the environment
source venv/bin/activate

# Upgrade pip to avoid potential installation issues
pip install --upgrade pip

# Install required packages
if [ "$OFFLINE" -eq 1 ]; then
    if [ ! -d "wheelhouse" ]; then
        echo "Offline mode selected but wheelhouse directory not found" >&2
        exit 1
    fi
    pip install --no-index --find-links=wheelhouse -r requirements.txt
else
    pip install -r requirements.txt
fi

echo "Environment is ready. Activate it with 'source venv/bin/activate'"
