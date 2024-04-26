#!/bin/bash

PREFIX=$1
HOSTNAME=$2

# point home to /var/lib/ndn/nlsr so keys will be stored there.
if [ ! -s /home/nlsr/unsigned_site.cert ]
then
  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-key-gen -n $PREFIX  > /home/nlsr/unsigned_site.cert"
  echo "$cmd" > /tmp/key_gen1.cmd
  sudo su - nlsr -c "$cmd"
  #sudo su - nlsr -c 'export HOME=/var/lib/ndn/nlsr/; ndnsec-key-gen -n $PREFIX  > /home/nlsr/unsigned_site.cert'

  # create info needed for UCLA approval
  echo "$HOSTNAME $PREFIX" > /home/nlsr/approval.info
  
fi

# seems that now we have to set a default identity:
if [ ! -s /home/nlsr/unsigned_nlsr.cert ]
then
  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-key-gen -n ${PREFIX}/nlsr  > /home/nlsr/unsigned_nlsr.cert"
  sudo su - nlsr -c "$cmd"
  #sudo su - nlsr -c 'export HOME=/var/lib/ndn/nlsr/; ndnsec-key-gen -n ${PREFIX}/nlsr > /home/nlsr/unsigned_nlsr.cert'
fi

cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-set-default -n ${PREFIX}/nlsr "
sudo su - nlsr -c "$cmd"
#sudo su - nlsr -c 'export HOME=/var/lib/ndn/nlsr/; ndnsec-set-default -n ${PREFIX}/nlsr'

