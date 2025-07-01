#!/usr/bin/env bash
# Simple helper script to create a Python virtual environment
# and install project dependencies.
set -e

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
pip install -r requirements.txt

echo "Environment is ready. Activate it with 'source venv/bin/activate'"
