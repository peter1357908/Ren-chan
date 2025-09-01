#!/bin/bash

# this stops the systemd service, and deletes the service setup.
# It also removes the pip environment and logs.

set -e  # Exit immediately if a command fails

# Make the current user own the service.
SERVICE_OWNER="${USER}"

sudo systemctl stop "ren-chan@${SERVICE_OWNER}"
sudo systemctl disable "ren-chan@${SERVICE_OWNER}"
sudo rm /etc/systemd/system/ren-chan@.service
sudo systemctl daemon-reload

# Navigate to project root
cd "$(dirname "$0")/.."

rm -r .venv/
rm logs/*.log
