#!/bin/bash

# Change directory to the root of the project
cd "$(dirname "${BASH_SOURCE[0]}")"/..

# Save status to file server
python3 framework/status-json.py > dist/file-server/status.json

# Done
echo -e "Status updated at $(date)"
