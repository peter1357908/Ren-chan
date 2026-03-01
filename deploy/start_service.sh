#!/bin/bash

# this script runs `pipenv install`, sets up the systemd service, and (re-)starts the service.
# (this is suitable for local testing; it does not do a `git pull`)

set -e  # Exit immediately if a command fails

# Make the current user own the service.
SERVICE_OWNER="${USER}"

# Navigate to project root
cd "$(dirname "$0")/.."

# Ensure pipenv uses a venv inside the project
export PIPENV_VENV_IN_PROJECT=1
pipenv install --deploy --ignore-pipfile

# Deploy the systemd service
sudo cp deploy/ren-chan@.service /etc/systemd/system/ren-chan@.service
sudo systemctl daemon-reload

# Start and enable the templated service for this user
sudo systemctl restart "ren-chan@${SERVICE_OWNER}"
sudo systemctl enable "ren-chan@${SERVICE_OWNER}"

echo "Service (re-)started and enabled for user ${SERVICE_OWNER}"
