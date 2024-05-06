#!/bin/sh

# Do not call this script directly
# It is only called by the crontab

set +e

echo -e "Running cron-1 at $(date)\n"

cd /repo

git pull
python3 framework/main.py

# Apply changes to the docker-compose.yml
# Also starts up any services that are not running
docker compose up -d
