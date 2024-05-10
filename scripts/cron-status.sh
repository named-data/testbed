#!/bin/bash

set -e

# Change directory to the root of the project
cd "$(dirname "${BASH_SOURCE[0]}")"/..

# Get variables in shell
source .env

# Save status to file server
STATUS=$(python3 framework/status-json.py)
echo -e "$STATUS" > dist/file-server/status.json

# Done
echo -e "Status updated at $(date)"

# Collect all statuses if enabled
if [[ -n "$COLLECT_STATUS_GLOBAL" ]]; then
    echo -e "Waiting before starting global status job ..."
    sleep 60

    GLOBAL_STATUS=$(python3 framework/status-global.py)
    echo -e "$GLOBAL_STATUS" > dist/file-server/status-global.json
fi
