#!/bin/bash
PID_FILE="./app.pid"

python3 bot.py > /dev/null 2>&1 &
NEW_PID=$!

echo $NEW_PID > "$PID_FILE"
echo "[START] New process started in the background with PID $NEW_PID"