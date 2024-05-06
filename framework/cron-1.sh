#!/bin/sh

# Do not call this script directly
# It is only called by the crontab

set -e

cd /repo

git pull
python3 framework/main.py

# TODO: what if docker-compose.yml changes