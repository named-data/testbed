#!/bin/bash

# This is the cron script for the master container
set +e

# Change directory to the root of the project
cd "$(dirname "${BASH_SOURCE[0]}")"/..

# Check if debug mode is enabled
source .env
if [[ -n "$DEBUG" ]]; then
    echo "Skipping job because DEBUG is enabled"
    exit 0
fi

# Prevent a thundering herd
WAIT="$((RANDOM % 120))"
echo "Random wait for ${WAIT} seconds ..."
sleep "${WAIT}"

git pull

PWD="${ROOT_DIR}" python3 framework/main.py

echo -e "Finished cron-master at $(date)"