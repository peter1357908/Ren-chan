#!/bin/bash
set -e  # Exit if any command fails
exec >./logs/deploy.log 2>&1

echo "[DEPLOY] Pulling latest code..."
git pull

echo "[DEPLOY] Installing/updating dependencies according to Pipfile.lock..."
pipenv install --deploy --ignore-pipfile

echo "[DEPLOY] Calling start.sh..."
./start.sh
echo "[DEPLOY] Deployment Done."
