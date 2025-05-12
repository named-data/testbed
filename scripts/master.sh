#!/bin/bash

# This script is used to run the master service.
# It should be called from the root of the project.

set -e

echo -e "Starting master service at $(date)" >&2

# Change directory to the root of the project
cd "$(dirname "${BASH_SOURCE[0]}")"/..

rm -f dist/.master-ready

# Skip if debug mode is enabled
source .env
if [[ -z "$DEBUG" ]]; then
    # Initial repo pull
    git config --global --add safe.directory /testbed
    git pull

    # Bootstrap all configuration files
    python3 framework/main.py --dry

    # Check and reissue certificates
    bash $(pwd)/scripts/cert-renew.sh
else
    echo -e "Skipping initial repo pull and bootstrap because DEBUG=1" >&2
fi

# End bootstrapping
date > dist/.master-ready

# Wait for 2 minutes before starting cron,
# so that all services becomes healthy first.
sleep 120

# Start crond
USER="$(whoami)"
CRON_DIR="/var/spool/cron/crontabs"
CRONTAB="$(pwd)/scripts/crontab-master"

chown "${USER}:${USER}" "${CRONTAB}"
rm -rf "${CRON_DIR}" && mkdir -p "${CRON_DIR}"
ln -s "${CRONTAB}" "${CRON_DIR}/${USER}"

# Use verbose logging for debugging
LOGLEVEL=8
if [[ -n "$DEBUG" ]]; then
    LOGLEVEL=0
fi

exec busybox crond -f -L /dev/stdout -l "${LOGLEVEL}" -c "${CRON_DIR}"
