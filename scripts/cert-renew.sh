#!/bin/bash

source "$(pwd)/scripts/utils.sh"

COMPOSE_PROFILES=$(python3 framework/service-profiles.py) || exit $?
export COMPOSE_PROFILES

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

reload_changed() {
    local service="$1" directory="$2" running
    if [[ -f "${directory}/.security-changed" ]]; then
        running=$(PWD="${ROOT_DIR:-$PWD}" docker compose ps --status running -q "$service") || return $?
        if [[ -n "$running" ]]; then
            PWD="${ROOT_DIR:-$PWD}" docker compose restart "$service" || return $?
        fi
        rm -f "${directory}/.security-changed"
    fi
}

# Optional services retain their own renewal and reload retry state.
renew_merkle() {
    local MERKLE_SERVICE="$1"
    local MERKLE_ENABLED MERKLE_DIR MERKLE_FORCE
    MERKLE_ENABLED=$(python3 framework/service-profiles.py --service "${MERKLE_SERVICE}") || return $?
    if [[ "${MERKLE_ENABLED}" == 1 ]]; then
        MERKLE_DIR="dist/${MERKLE_SERVICE}"
        if [[ -n "$2" ]]; then
            touch "${MERKLE_DIR}/.renew-pending"
        fi
        MERKLE_FORCE=""
        if [[ -f "${MERKLE_DIR}/.renew-pending" ]]; then
            MERKLE_FORCE="--force"
        fi
        if bash "${MERKLE_DIR}/renew.sh" ${MERKLE_FORCE:+"${MERKLE_FORCE}"}; then
            rm -f "${MERKLE_DIR}/.renew-pending"
            reload_changed "$MERKLE_SERVICE" "$MERKLE_DIR" || return $?
        else
            echo "${MERKLE_SERVICE} credential renewal failed; core services renewed, log will retry next poll" >&2
        fi
    fi
}

# Finish existing NFD renewals and reloads before processing the separate network.
renew_merkle ndnd-merkle "${FORCE}" || exit $?

# A site-certificate change on NFD must not force unrelated NDNd credentials.
NDND_FORCE=${HAS_FORCE:+--force}
DV_ENABLED=$(python3 framework/service-profiles.py --service ndnd-dv) || exit $?
if [[ "${DV_ENABLED}" == 1 ]]; then
    SITE_CA_ENABLED=$(python3 framework/service-profiles.py --service ndnd-site-ca) || exit $?
    if [[ "${SITE_CA_ENABLED}" == 1 ]]; then
        SITE_CA_DIR=dist/ndnd-site-ca
        bash "${SITE_CA_DIR}/renew.sh" ${NDND_FORCE:+"${NDND_FORCE}"} || exit $?
        reload_changed ndnd-site-ca "${SITE_CA_DIR}" || exit $?
    fi
    DV_DIR=dist/ndnd-dv
    bash "${DV_DIR}/renew.sh" ${NDND_FORCE:+"${NDND_FORCE}"} || exit $?
    reload_changed ndnd-dv "${DV_DIR}" || exit $?
    NETWORK_REPO_DIR=dist/ndnd-network-repo
    bash "${NETWORK_REPO_DIR}/renew.sh" ${NDND_FORCE:+"${NDND_FORCE}"} || exit $?
    reload_changed ndnd-network-repo "${NETWORK_REPO_DIR}" || exit $?
fi

renew_merkle ndnd-network-merkle "${NDND_FORCE}" || exit $?
