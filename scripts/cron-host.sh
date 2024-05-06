#!/bin/bash

# This job must be run every 5 minutes on the host machine

sleep 20 # run in the middle of the minute

# Change directory to the root of the project
cd "$(dirname "${BASH_SOURCE[0]}")"/..

# Ensure services are running
docker compose up -d --remove-orphans