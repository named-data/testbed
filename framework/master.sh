#!/bin/sh

# This script is used to run the master service.
# It should be called from the root of the project.

# Clear ready flag
rm -f dist/.master-ready

# Perform initial rendering
python3 framework/main.py --dry

# Set ready flag
date > dist/.master-ready

# Sleep forever
while true; do
    sleep 10000000
done