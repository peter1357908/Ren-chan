#!/bin/bash
PID_FILE="./app.pid"

python3 bot.py &
NEW_PID=$!

echo $NEW_PID > "$PID_FILE"
echo "[START] New process started with PID $NEW_PID"