#!/bin/sh

# This script is used to run the master service.
# It should be called from the root of the project.

set -e

rm -f dist/.master-ready

git config --global --add safe.directory /repo
git pull

python3 framework/main.py

date > dist/.master-ready

cp framework/crontab "/var/spool/cron/crontabs/$(whoami)"
exec busybox crond -f -L /dev/stdout
