#!/bin/bash

START_DATE="201612010000"
END_DATE="201812010000"
#PREFIX=$1
#HOSTNAME=$2
#
## this next step must take place on UCLA where the root cert is.
#cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-cert-gen -S $START_DATE -E $END_DATE -s /ndn -r /home/nlsr/${HOSTNAME}_unsigned_site.cert > /home/nlsr/${HOSTNAME}_site.cert"
#

# For each file ANSIBLE_*_approval.info approved the associated cert named ANSIBLE_*_unsigned_site.cert
# and  produce a signed cert and put it in the file ANSIBLE_*_site.cert.

APPROVAL_INFO_FILES=`ls /home/nlsr/ANSIBLE_*approval.info`
for f in $APPROVAL_INFO_FILES
do
  HOSTNAME=`cat $f | cut -d ' ' -f 1`
  PREFIX=`cat $f | cut -d ' ' -f 2`
  cmd="export HOME=/var/lib/ndn/nlsr/; ndnsec-cert-gen -S $START_DATE -E $END_DATE -s /ndn -r /home/nlsr/ANSIBLE_${HOSTNAME}_unsigned_site.cert > /home/nlsr/ANSIBLE_${HOSTNAME}_site.cert"
  sudo su - nlsr -c "$cmd"
  rm -f $f
done
