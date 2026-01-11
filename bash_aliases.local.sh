#!/bin/bash

# Bash aliases for local 3-node testbed
# Usage: source bash_aliases.local.sh

exec_with_tty() {
    if [[ -t 0 && ! -p /dev/stdout ]]; then
        docker exec -it "$@"
    else
        docker exec -i "$@"
    fi
}

# NFD commands for each node
alias nfdc1="exec_with_tty testbed-local-nfd1-1 nfdc"
alias nfdc2="exec_with_tty testbed-local-nfd2-1 nfdc"
alias nfdc3="exec_with_tty testbed-local-nfd3-1 nfdc"

# NLSR commands for each node
alias nlsrc1="exec_with_tty testbed-local-nlsr1-1 nlsrc"
alias nlsrc2="exec_with_tty testbed-local-nlsr2-1 nlsrc"
alias nlsrc3="exec_with_tty testbed-local-nlsr3-1 nlsrc"

# NDN tools for each node
for tool in ndnping ndnpingserver ndnpeek ndnpoke ndndump ndndissect; do
    alias "${tool}1=exec_with_tty testbed-local-ndnpingserver1-1 ${tool}"
    alias "${tool}2=exec_with_tty testbed-local-ndnpingserver2-1 ${tool}"
    alias "${tool}3=exec_with_tty testbed-local-ndnpingserver3-1 ${tool}"
done

# Quick status check
local_status() {
    echo "=== Node 1 (LOCAL1) ==="
    docker exec testbed-local-nfd1-1 nfdc status report 2>/dev/null | head -20
    echo ""
    echo "=== Node 2 (LOCAL2) ==="
    docker exec testbed-local-nfd2-1 nfdc status report 2>/dev/null | head -20
    echo ""
    echo "=== Node 3 (LOCAL3) ==="
    docker exec testbed-local-nfd3-1 nfdc status report 2>/dev/null | head -20
}

# Check faces on all nodes
local_faces() {
    echo "=== Node 1 Faces ==="
    docker exec testbed-local-nfd1-1 nfdc face list 2>/dev/null
    echo ""
    echo "=== Node 2 Faces ==="
    docker exec testbed-local-nfd2-1 nfdc face list 2>/dev/null
    echo ""
    echo "=== Node 3 Faces ==="
    docker exec testbed-local-nfd3-1 nfdc face list 2>/dev/null
}

# Check NLSR routing on all nodes
local_routes() {
    echo "=== Node 1 Routes ==="
    docker exec testbed-local-nlsr1-1 nlsrc status 2>/dev/null || echo "NLSR not ready"
    echo ""
    echo "=== Node 2 Routes ==="
    docker exec testbed-local-nlsr2-1 nlsrc status 2>/dev/null || echo "NLSR not ready"
    echo ""
    echo "=== Node 3 Routes ==="
    docker exec testbed-local-nlsr3-1 nlsrc status 2>/dev/null || echo "NLSR not ready"
}

echo "Local testbed aliases loaded!"
echo "Commands: nfdc1, nfdc2, nfdc3, nlsrc1, nlsrc2, nlsrc3"
echo "Tools: ndnping1, ndnping2, ndnping3, etc."
echo "Functions: local_status, local_faces, local_routes"
