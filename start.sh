#!/bin/bash
PID_FILE="./app.pid"
exec >./logs/start.log 2>&1

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

# we expect no stdout or stderr; any logging should be handled by the app explicitly
pipenv run python3 bot.py &
NEW_PID=$!

echo $NEW_PID > "$PID_FILE"
echo "[START] New process started in the background with PID $NEW_PID"