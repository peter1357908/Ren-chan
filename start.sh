#!/bin/bash
PID_FILE="./app.pid"

# we expect no stdout or stderr; any logging should be handled by the app explicitly
python3 bot.py > /dev/null 2>&1 &
NEW_PID=$!

echo $NEW_PID > "$PID_FILE"
echo "[START] New process started in the background with PID $NEW_PID"