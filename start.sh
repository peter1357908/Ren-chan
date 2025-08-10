#!/bin/bash
PID_FILE="./app.pid"
exec > ./logs/start.log 2>&1

# kill the bot if it's currently running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "[START] Stopping old process (PID $OLD_PID)..."
        kill $OLD_PID
        sleep 2
    else
        echo "[START] No running process found for PID $OLD_PID"
    fi
fi

# app loggings and exceptions should be in `app.log`. Here `python.log` should only capture
# some pipenv logs and unexpected stdout/stderr stuff.
pipenv run python3 bot.py > ./logs/python.log 2>&1 &
NEW_PID=$!

echo $NEW_PID > "$PID_FILE"
echo "[START] New process started in the background with PID $NEW_PID"