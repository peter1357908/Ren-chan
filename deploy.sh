#!/bin/bash
set -e  # Exit if any command fails

PID_FILE="./app.pid"

echo "[DEPLOY] Pulling latest code..."
git pull

echo "[DEPLOY] Installing/updating dependencies according to Pipfile.lock..."
pipenv install --deploy --ignore-pipfile

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "[DEPLOY] Stopping old process (PID $OLD_PID)..."
        kill $OLD_PID
        sleep 2
    else
        echo "[DEPLOY] No running process found for PID $OLD_PID"
    fi
fi

echo "[DEPLOY] Starting new process in Pipenv environment..."
pipenv run ./start.sh
echo "[DEPLOY] Deployment Done."
