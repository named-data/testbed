#!/bin/bash

# Declare all command line flags here
HAS_FORCE=$(echo $@ | grep -ow "\-\-force")

# Allow call to fail and return exit code
allow_fail_status=0
function allow_fail {
    set +e;
    $@; allow_fail_status=$?;
    set -e;
}

# Get the directory of the script
function script_dir {
    echo "$(dirname "${BASH_SOURCE[0]}")"
}

# Change to the directory of the script
function cd_script_dir {
    cd "$(script_dir)"
}

# Get CSR for a key or generate a new keypair
function get_csr {
    local key_name=$1
    allow_fail ndnsec sign-req "${key_name}" 2> /dev/null
    if [ $allow_fail_status -ne 0 ]; then
        echo -e "Generating new keypair for ${key_name}" >&2
        ndnsec key-gen -n "${key_name}"
    else
        echo -e "Using existing keypair for ${key_name}" >&2
    fi
}

# Check if a certificate needs to be renewed
function needs_renewal {
    local cert_path=$1
    if [[ ! -f "${cert_path}" || -n "${HAS_FORCE}" ]]; then
        echo -e "1"
    else
        echo -e "${cert_path} exists, skipping ..." >&2
    fi
}

# Cleanup intermediate files for cert renewal scripts
function renew_cleanup {
    rm -f ${WORKING_DIR}/*.csr
}
