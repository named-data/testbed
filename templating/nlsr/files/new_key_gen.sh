#!/bin/bash
# default_prefix
PREFIX=$1
# ansible_user
OPERATOR=$2  
# inventory_hostname
HOSTNAME=$3
# router_name
ROUTER=$4

# One time, clean out all NLSR keys and redo
sudo rm /etc/ndn/nlsr/keys/operator.cert
sudo rm /etc/ndn/nlsr/keys/router.cert
sudo rm -rf /var/lib/ndn/nlsr/.ndn

#if [ ! -s /home/nlsr/unsigned_nlsr.cert ]
#then
#  sudo su - nlsr -c "export HOME=/var/lib/ndn/nlsr/; ndnsec-key-gen -n ${PREFIX}/nlsr > /home/nlsr/unsigned_nlsr.cert"
#  sudo su - nlsr -c "export HOME=/var/lib/ndn/nlsr/; ndnsec-set-default -n ${PREFIX}/nlsr"
#fi

if [ ! -s /etc/ndn/nlsr/keys/operator.cert ]
then
  sudo su - nlsr -c "export HOME=/var/lib/ndn/nlsr/; ndnsec-key-gen -n ${PREFIX}/%C1.Operator/${OPERATOR} > ~nlsr/unsigned_operator.cert"
  # Using old legacy CA:
  #sudo su - ndnsec -c "ndnsec-cert-gen -S 201803010000 -E 20280301000 -s ${PREFIX} -r ~nlsr/unsigned_operator.cert > /tmp/operator.cert"
  # Using new ndncert-ca:
  sudo su - root -c "export HOME=/var/lib/ndn/ndncert-ca/; ndnsec-cert-gen -S 202204010000 -E 20320401000 -s ${PREFIX} -r ~nlsr/unsigned_operator.cert > /tmp/operator.cert"
  sudo su - root -c "chown nlsr.nlsr /tmp/operator.cert"

  sudo su - nlsr -c "cp /tmp/operator.cert /etc/ndn/nlsr/keys/operator.cert"
  sudo su - nlsr -c "export HOME=/var/lib/ndn/nlsr/; ndnsec-cert-install -f /etc/ndn/nlsr/keys/operator.cert"
  sudo su - nlsr -c "rm /tmp/operator.cert"
fi

#if [ ! -s /etc/ndn/nlsr/keys/operator.cert ]
#then
#  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-key-gen -n ${PREFIX}/%C1.Operator/${OPERATOR} > ~nlsr/unsigned_operator.cert"
#  sudo su - nlsr -c "$cmd"
#
#  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-cert-gen -S 201802010000 -E 202802010000 -s ${PREFIX} -r ~nlsr/unsigned_operator.cert > /etc/ndn/nlsr/keys/operator.cert"
#  sudo su - nlsr -c "$cmd"
#  sudo su - nlsr -c "export HOME=/var/lib/ndn/nlsr/; ndnsec-cert-install -f /etc/ndn/nlsr/keys/operator.cert"
#fi

if [ ! -s /etc/ndn/nlsr/keys/router.cert ]
then
  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-key-gen -n ${PREFIX}/%C1.Router/${ROUTER} > ~nlsr/unsigned_router.cert"
  sudo su - nlsr -c "$cmd"

  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-cert-gen -S 201802010000 -E 202802010000 -s ${PREFIX}/%C1.Operator/${OPERATOR} -r ~nlsr/unsigned_router.cert > /etc/ndn/nlsr/keys/router.cert"
  sudo su - nlsr -c "$cmd"
  sudo su - nlsr -c "export HOME=/var/lib/ndn/nlsr/; ndnsec-cert-install -f /etc/ndn/nlsr/keys/router.cert"
fi

