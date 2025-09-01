#!/bin/bash

# this script stops and disables the service.

set -e  # Exit immediately if a command fails

# Make the current user own the service.
SERVICE_OWNER="${USER}"

sudo systemctl stop "ren-chan@${SERVICE_OWNER}"
sudo systemctl disable "ren-chan@${SERVICE_OWNER}"
