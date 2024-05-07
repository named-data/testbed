#!/bin/bash

# This script is used to run the master service.
# It should be called from the root of the project.

set -e

echo -e "Starting master service at $(date)"

rm -f dist/.master-ready

git config --global --add safe.directory /testbed
git pull

# Bootstrap all configuration files
export TESTBED_BOOTSTRAP=1
python3 framework/main.py --dry

# Check and reissue certificates
bash dist/ndncert/renew.sh
bash dist/nlsr/renew.sh
bash dist/ndn-python-repo/renew.sh

# End bootstrapping
unset TESTBED_BOOTSTRAP
date > dist/.master-ready

# Wait for 2 minutes before starting cron,
# so that all services becomes healthy first.
sleep 120

mkdir -p "/var/spool/cron/crontabs"
cp scripts/crontab "/var/spool/cron/crontabs/$(whoami)"
exec busybox crond -f -L /dev/stdout
