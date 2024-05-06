#!/bin/sh

# Do not call this script directly
# It is only called by the crontab

set +e

echo -e "Running cron-1 at $(date)\n"

cd /repo

git pull

PWD=$ROOT_DIR python3 framework/main.py
