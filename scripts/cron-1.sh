#!/bin/bash

# Do not call this script directly
# It is only called by the crontab

set +e

cd /testbed
git pull

PWD=$ROOT_DIR python3 framework/main.py

echo -e "Finished cron-1 at $(date)"