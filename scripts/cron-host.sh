#!/bin/bash

# This job must be run every 6 minutes on the host machine

# Change directory to the root of the project
cd "$(dirname "${BASH_SOURCE[0]}")"/..
source "$(pwd)/scripts/utils.sh"

# Check if debug mode is enabled
source .env
if [[ -n "$DEBUG" ]]; then
    echo -e "Skipping job because DEBUG is enabled" >&2
    exit 0
fi

# Sleep for random time
if [[ -z "$SKIP_SLEEP" ]]; then
    sleep 10
    random_sleep 60
fi

# Recreate the master container separately first
# Even when all others depend on master, we don't want
# to recreate everything when master is updated
docker compose up -d master --no-deps

# Resolve service profiles from Git configuration inside the existing master image.
COMPOSE_PROFILES=$(docker compose exec -T master python3 framework/service-profiles.py) || exit $?
export COMPOSE_PROFILES

# Ensure services are running
docker compose up -d --remove-orphans || exit $?

# Services must be running before their management commands can install routes.
docker compose exec -T -e PWD="$PWD" master python3 framework/ndnd-network-init.py || exit $?

echo -e "Finished cron-host at $(date)" >&2
