#!/bin/bash

source "$(pwd)/scripts/utils.sh"

NDNCERT_CERTFILE="$(pwd)/dist/ndncert/site.ndncert"

FORCE=""
if [[ $(needs_renewal "${NDNCERT_CERTFILE}") ]]; then
    echo -e "Certificate needs renewal, using --force" >&2
    FORCE="--force"
fi

# Check and reissue certificates
bash "$(pwd)/dist/ndncert/renew.sh" "${FORCE}"
bash "$(pwd)/dist/nlsr/renew.sh" "${FORCE}"
bash "$(pwd)/dist/ndn-python-repo/renew.sh" "${FORCE}"

# Restart containers if force
if [[ -n "${FORCE}" ]]; then
    docker compose restart nlsr ndncert serve-certs ndn-python-repo
fi
