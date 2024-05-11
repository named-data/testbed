#!/bin/bash

# This job must be run every 6 minutes on the host machine

# Change directory to the root of the project
cd "$(dirname "${BASH_SOURCE[0]}")"/..
source "$(pwd)/scripts/utils.sh"

# Check if debug mode is enabled
source .env
if [[ -n "$DEBUG" ]]; then
    echo "Skipping job because DEBUG is enabled"
    exit 0
fi

# Sleep for random time
sleep 10
random_sleep 60

# Ensure services are running
docker compose up -d --remove-orphans