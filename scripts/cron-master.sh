#!/bin/bash

# This is the cron script for the master container
set +e

# Change directory to the root of the project
cd "$(dirname "${BASH_SOURCE[0]}")"/..
source "$(pwd)/scripts/utils.sh"

# Check if debug mode is enabled
source .env
if [[ -n "$DEBUG" ]]; then
    echo "Skipping job because DEBUG is enabled"
    exit 0
fi

# Prevent a thundering herd
random_sleep 120

git pull

PWD="${ROOT_DIR}" python3 framework/main.py

echo -e "Finished cron-master at $(date)"