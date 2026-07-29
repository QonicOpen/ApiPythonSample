#!/usr/bin/env bash
# Superset worktree setup script for ApiPythonSample
set -euo pipefail

BRANCH_NAME="${1:-$(git rev-parse --abbrev-ref HEAD)}"

echo "Setting up ApiPythonSample worktree for branch: $BRANCH_NAME"

# Copy env files from the root repo if available
if [ -n "${SUPERSET_ROOT_PATH:-}" ]; then
  for envfile in .env .env.example; do
    if [ -f "$SUPERSET_ROOT_PATH/$envfile" ]; then
      cp "$SUPERSET_ROOT_PATH/$envfile" "./$envfile"
      echo "Copied $envfile from root"
    fi
  done
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "Setup complete for branch: $BRANCH_NAME"
echo "  - Run: python sample.py"
echo "  - Configure .env with your Client ID and Secret first"
