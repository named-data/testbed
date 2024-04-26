#!/bin/bash
# default_prefix
PREFIX=$1
# ansible_user
OPERATOR=$2  
# inventory_hostname
HOSTNAME=$3
# router_name
ROUTER=$4

# point home to /var/lib/ndn/nlsr so keys will be stored there.
# seems that now we have to set a default identity:
cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-set-default -n ${PREFIX}/nlsr "
#echo "$cmd" > /tmp/nlsr.cmd
sudo su - nlsr -c "$cmd"

if [ ! -s /etc/ndn/nlsr/keys/operator.cert ]
then
  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-key-gen -n ${PREFIX}/%C1.Operator/${OPERATOR} > ~nlsr/unsigned_operator.cert"
  sudo su - nlsr -c "$cmd"

  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-cert-gen -S 201802010000 -E 202802010000 -s ${PREFIX} -r ~nlsr/unsigned_operator.cert > /etc/ndn/nlsr/keys/operator.cert"
  sudo su - nlsr -c "$cmd"
fi

if [ ! -s /etc/ndn/nlsr/keys/router.cert ]
then
  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-key-gen -n ${PREFIX}/%C1.Router/${ROUTER} > ~nlsr/unsigned_router.cert"
  sudo su - nlsr -c "$cmd"

  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-cert-gen -S 201802010000 -E 202802010000 -s ${PREFIX}/%C1.Operator/${OPERATOR} -r ~nlsr/unsigned_router.cert > /etc/ndn/nlsr/keys/router.cert"
  sudo su - nlsr -c "$cmd"
fi


# now that we are all approved, remove the approval.info file
if [ -f ~nlsr/approval.info ]
then
  sudo rm ~nlsr/approval.info
fi
