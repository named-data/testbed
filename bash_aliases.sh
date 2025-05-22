#!/bin/bash

# This file provides aliases for common ndn tools
# The containers should be running to use any of these

exec_with_tty() {
    if [[ -t 0 && ! -p /dev/stdout ]]; then
        docker exec -it "$@"
    else
        docker exec -i "$@"
    fi
}

for tool in ndnpeek ndnpoke ndnget ndnserve ndnping ndnpingserver ndndump ndndissect; do
    alias "${tool}=exec_with_tty testbed-ndnpingserver-1 ${tool}"
done

alias nfdc="exec_with_tty testbed-nfd-1 nfdc"
alias nlsrc="exec_with_tty testbed-nlsr-1 nlsrc"
