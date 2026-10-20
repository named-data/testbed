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

DV_ENABLED=$(python3 framework/service-profiles.py --service ndnd-dv) || exit $?
if [[ "${DV_ENABLED}" == 1 ]]; then
    NDND_SIGNER_ENABLED=$(python3 framework/service-profiles.py --service ndnd-root-http-ca) || exit $?
    if [[ "${NDND_SIGNER_ENABLED}" == 1 ]]; then
        COMPOSE_PROFILES=$(python3 framework/service-profiles.py) || exit $?
        export COMPOSE_PROFILES
        PWD="${ROOT_DIR:-$PWD}" docker compose up -d --no-deps --wait --wait-timeout 30 ndnd-root-http-ca || exit $?
    fi
    SITE_CA_ENABLED=$(python3 framework/service-profiles.py --service ndnd-go-ca) || exit $?
    if [[ "${SITE_CA_ENABLED}" == 1 ]]; then
        SITE_CA_CONFIG_DIR=dist/ndnd-site-ca-config
        SITE_CA_DIR=dist/ndnd-site-ca-independent
        bash "${PWD}/${SITE_CA_CONFIG_DIR}/renew.sh" ${FORCE:+"${FORCE}"} || exit $?
        if [[ -f "${SITE_CA_DIR}/.security-changed" ]]; then
            RUNNING_CA=$(PWD="${ROOT_DIR:-$PWD}" docker compose ps --status running -q ndnd-go-ca) || exit $?
            if [[ -n "${RUNNING_CA}" ]]; then
                PWD="${ROOT_DIR:-$PWD}" docker compose restart ndnd-go-ca || exit $?
            fi
            rm -f "${SITE_CA_DIR}/.security-changed"
        fi
    fi
    DV_DIR=dist/ndnd-dv-independent
    bash "${DV_DIR}/renew.sh" ${FORCE:+"${FORCE}"} || exit $?
    if [[ -f "${DV_DIR}/.security-changed" ]]; then
        RUNNING_DV=$(PWD="${ROOT_DIR:-$PWD}" docker compose ps --status running -q ndnd-dv) || exit $?
        if [[ -n "${RUNNING_DV}" ]]; then
            PWD="${ROOT_DIR:-$PWD}" docker compose restart ndnd-dv || exit $?
        fi
        rm -f "${DV_DIR}/.security-changed"
    fi
fi

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

# Optional services run after the core renewals and retain their own retry state.
MERKLE_ENABLED=$(python3 framework/service-profiles.py --service ndnd-merkle) || exit $?
if [[ "${MERKLE_ENABLED}" == 1 ]]; then
    MERKLE_DIR=dist/ndnd-merkle
    if [[ -n "${FORCE}" ]]; then
        touch "${MERKLE_DIR}/.renew-pending"
    fi
    MERKLE_FORCE=""
    if [[ -f "${MERKLE_DIR}/.renew-pending" ]]; then
        MERKLE_FORCE="--force"
    fi
    if bash "${MERKLE_DIR}/renew.sh" ${MERKLE_FORCE:+"${MERKLE_FORCE}"}; then
        rm -f "${MERKLE_DIR}/.renew-pending"
        if [[ -f "${MERKLE_DIR}/.security-changed" ]]; then
            RUNNING_LOG=$(PWD="${ROOT_DIR:-$PWD}" docker compose ps --status running -q ndnd-merkle) || exit $?
            if [[ -n "${RUNNING_LOG}" ]]; then
                PWD="${ROOT_DIR:-$PWD}" docker compose restart ndnd-merkle || exit $?
            fi
            rm -f "${MERKLE_DIR}/.security-changed"
        fi
    else
        echo "NDNd Merkle credential renewal failed; core services renewed, log will retry next poll" >&2
    fi
fi
