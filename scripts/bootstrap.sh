#!/usr/bin/env bash
# Simple bootstrap script to install all dependencies needed for
# running tests and linters. This sets up the Python virtual
# environment, installs Python packages, and fetches frontend
# assets.
set -e

# Create Python virtual environment and install packages
./setup_env.sh "$@"
source venv/bin/activate

# Install frontend node modules and build assets
if [ -f package.json ]; then
    npm ci
    npm run build
fi

echo "Bootstrap complete. Activate the virtualenv with 'source venv/bin/activate' and run 'pytest' or 'flake8' as needed."
