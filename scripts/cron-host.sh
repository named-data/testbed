#!/bin/bash

# This job must be run every 5 minutes on the host machine

sleep 20 # run in the middle of the minute

# Change directory to the root of the project
cd "$(dirname "${BASH_SOURCE[0]}")"/..

# Check if debug mode is enabled
source .env
if [[ -n "$DEBUG" ]]; then
    echo "Skipping job because DEBUG is enabled"
    exit 0
fi

# Ensure services are running
docker compose up -d --remove-orphans