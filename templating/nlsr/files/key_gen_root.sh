#!/bin/bash

PREFIX=/ndn

# point home to /var/lib/ndn/nlsr so keys will be stored there.
if [ ! -s /home/nlsr/root.cert ]
then
  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-key-gen -i /ndn  >& /home/nlsr/unsigned_root.cert"
  echo "$cmd" > /tmp/key_gen1.cmd
  sudo su - nlsr -c "$cmd"

  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-cert-gen -S 20180201000000 -E 20280201000000 -s /ndn -r /home/nlsr/unsigned_root.cert  > /home/nlsr/root.cert"
  echo "$cmd" > /tmp/key_gen1.cmd
  sudo su - nlsr -c "$cmd"
fi

