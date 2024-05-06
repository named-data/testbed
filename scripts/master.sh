#!/bin/sh

# This script is used to run the master service.
# It should be called from the root of the project.

set -e

echo -e "Starting master service at $(date)\n"

rm -f dist/.master-ready

git config --global --add safe.directory /repo
git pull

python3 framework/main.py --dry

date > dist/.master-ready

# Wait for 2 minutes before starting cron,
# so that all services becomes healthy first.
sleep 120

cp scripts/crontab "/var/spool/cron/crontabs/$(whoami)"
exec busybox crond -f -L /dev/stdout
