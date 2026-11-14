#!/bin/bash

# This is the cron script for the master container
set +e

# Change directory to the root of the project
cd "$(dirname "${BASH_SOURCE[0]}")"/..
source "$(pwd)/scripts/utils.sh"

# Check if debug mode is enabled
source .env
if [[ -n "$DEBUG" ]]; then
    echo -e "Skipping job because DEBUG is enabled" >&2
    exit 0
fi

# Prevent a thundering herd
if [[ -z "$SKIP_SLEEP" ]]; then
    random_sleep 120
fi

# Remove git lock file if it exists and pull the latest changes
rm -f .git/index.lock
git pull

# Render new service templates before certificate provisioning on an existing node.
PWD="${ROOT_DIR}" python3 framework/main.py || exit $?

# Renew certificates if needed
bash $(pwd)/scripts/cert-renew.sh || exit $?

# Restore runtime forwarding entries after rendered services or credentials changed.
PWD="${ROOT_DIR:-$PWD}" python3 framework/ndnd-network-init.py || exit $?

echo -e "Finished cron-master at $(date)" >&2
