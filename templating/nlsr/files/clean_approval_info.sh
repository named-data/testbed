#!/bin/bash

DIR=$1

#ANSIBLE_WU_EBONY_approval.info
#ANSIBLE_WU_EBONY_site.cert

echo "DIR: $DIR" > /tmp/cleanup
pwd >> /tmp/cleanup
cd roles/nlsr/files
APPROVED=`ls ANSIBLE_*_site.cert | grep -v unsigned`
echo "APPROVED: $APPROVED" >> /tmp/cleanup

for f in $APPROVED
do
  echo "f: $f" >> /tmp/cleanup
  HOSTNAME1=`echo $f | cut -c  9-`
  echo "HOSTNAME1: $HOSTNAME1" >> /tmp/cleanup
  HOSTNAME2=`echo $HOSTNAME1 | rev | cut -c 11-| rev`
  echo "HOSTNAME2: $HOSTNAME2" >> /tmp/cleanup
  # remove the approval file
  APPROVAL="ANSIBLE_${HOSTNAME2}_approval.info"
  echo "APPROVAL: $APPROVAL" >> /tmp/cleanup
  if [ -f $APPROVAL ]
  then
    rm -f $APPROVAL
  fi

done
