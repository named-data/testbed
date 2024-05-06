#!/bin/bash

set -e

# Run the init script in background
/bin/bash /config/nfd-init.sh &

# Start NFD
exec /usr/bin/nfd --config /config/nfd.conf