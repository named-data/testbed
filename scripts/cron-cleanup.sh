#!/bin/bash

# Cleanup cron job run inside master container
set +e

# Remove unused docker images
docker image prune -a -f
