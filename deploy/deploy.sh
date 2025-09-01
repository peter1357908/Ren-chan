#!/bin/bash

# this script runs `git pull` and `pipenv install`, sets up the systemd service,
# and (re-)starts the service.

set -e  # Exit immediately if a command fails

# Make the current user own the service.
SERVICE_OWNER="${USER}"

# Navigate to project root
cd "$(dirname "$0")/.."

# Pull latest changes
git pull

# Ensure pipenv uses a venv inside the project
export PIPENV_VENV_IN_PROJECT=1
pipenv install --deploy --ignore-pipfile

# Deploy the systemd service
sudo cp deploy/ren-chan@.service /etc/systemd/system/ren-chan@.service
sudo systemctl daemon-reload

# Start and enable the templated service for this user
sudo systemctl restart "ren-chan@${SERVICE_OWNER}"
sudo systemctl enable "ren-chan@${SERVICE_OWNER}"

echo "Deployment complete for user ${SERVICE_OWNER}"
