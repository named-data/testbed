#!/bin/bash

source "$(pwd)/scripts/utils.sh"

NDNCERT_CERTFILE="$(pwd)/dist/ndncert/site.ndncert"

FORCE=""
if [[ $(needs_renewal "${NDNCERT_CERTFILE}") ]]; then
    echo -e "Certificate needs renewal, using --force" >&2
    FORCE="--force"
fi

# Check and reissue certificates
bash "$(pwd)/dist/ndncert/renew.sh" "${FORCE}" || exit $?
# Keep dependent renewals/reloads pending across a partially failed site renewal.
if [[ -f dist/ndncert/.security-changed ]]; then
    FORCE="--force"
fi
bash "$(pwd)/dist/nlsr/renew.sh" "${FORCE}" || exit $?
bash "$(pwd)/dist/ndn-python-repo/renew.sh" "${FORCE}" || exit $?
bash "$(pwd)/dist/ndnd-repo/renew.sh" ${FORCE:+"${FORCE}"} || exit $?

# Restart containers if force
if [[ -n "${FORCE}" ]]; then
    PWD="${ROOT_DIR:-$PWD}" docker compose restart nlsr ndncert serve-certs ndn-python-repo || exit $?
    rm -f dist/ndncert/.security-changed
fi

# The NDNd certificate or public chain can change independently of the site CA.
# During bootstrap the first start loads the credentials; running services reload them.
if [[ -f dist/ndnd-repo/.security-changed ]]; then
    RUNNING_REPO=$(PWD="${ROOT_DIR:-$PWD}" docker compose ps --status running -q ndnd-repo) || exit $?
    if [[ -n "${RUNNING_REPO}" ]]; then
        PWD="${ROOT_DIR:-$PWD}" docker compose restart ndnd-repo || exit $?
    fi
    rm -f dist/ndnd-repo/.security-changed
fi
