#!/bin/bash
PID_FILE="./app.pid"
# print to both stdout and to a file. Matters for GitHub Actions and for printing to
# the python log when run with `subprocess.Popen(["./start.sh"])`
exec > >(tee ./logs/start.log) 2>&1

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

# app loggings should be in `app.log`. Here `python.log` should only capture
# the tee'd stdout from running `subprocess.Popen(["./start.sh"])`, etc.
pipenv run python3 bot.py > ./logs/python.log 2>&1 &
NEW_PID=$!

echo $NEW_PID > "$PID_FILE"
echo "[START] New process started in the background with PID $NEW_PID"