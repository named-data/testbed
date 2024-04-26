#!/bin/bash

# Tell bash to ignores errors in this script:
set +e

# Some issues with startup time, we need to sleep to make sure nfd is fully up

sleep 15

# set default strategy to best-route (bestroute2)

/usr/bin/nfdc strategy set  ndn:/ ndn:/localhost/nfd/strategy/best-route


# set broadcast strategy
/usr/bin/nfdc strategy set  /ndn/multicast /localhost/nfd/strategy/multicast
/usr/bin/nfdc strategy set  /ndn/broadcast /localhost/nfd/strategy/multicast
/usr/bin/nfdc strategy set  /localhost     /localhost/nfd/strategy/multicast
# set /ndn/irl-workspace/32=sync with
/usr/bin/nfdc strategy set  /ndn/irl-workspace/32=sync  /localhost/nfd/strategy/multicast
/usr/bin/nfdc strategy set  /ndn/ndncomm2024/32=sync  /localhost/nfd/strategy/multicast
/usr/bin/nfdc strategy set  /ndn/localfirst/meetingnotes/32=sync /localhost/nfd/strategy/multicast

# default local access strategy
nfdc strategy set  ndn:/ndn/edu/ucla ndn:/localhost/nfd/strategy/access


nfdc strategy set  ndn:/ndn/edu/ucla/remap ndn:/localhost/nfd/strategy/best-route



## Special stuff for NDN SIGCOMM demo:
#nfdc strategy set /ndn/edu/wustl/jdd ndn:/localhost/nfd/strategy/asf/%FD%02
##nfdc strategy set /ndn/edu/wustl/jdd ndn:/localhost/nfd/strategy/asf/%FD%02/n-silent-timeouts=4
#nfdc strategy set /ndn/edu/wustl/jdd ndn:/localhost/nfd/strategy/asf/%FD%02/n-silent-timeouts=2


# Build the faces that NLSR will need:
  # UCLA  Neighbors: {'SAVI': {'link_cost': 40}, 'ARIZONA': {'link_cost': 25}, 'WU': {'link_cost': 30}, 'ANYANG': {'link_cost': 100}}


iptables -A INPUT -s 142.1.174.177  -j DROP

# just in case an on-demand face was created since NFD started, destroy it. 
# This is a temporary fix because an update of a face with mtu change does not currently work.
nfdc face destroy udp4://142.1.174.177:6363

## Test reliability just between ARIZONA and WU
#
#nfdc face create udp4://142.1.174.177:6363 persistency permanent mtu 1450
#

## Use reliability everywhere. Leave it off to LACL until we have them update.
## once LACL gets updated, need to run this again so all nodes go to LACL with reliability turned on
#
#nfdc face create udp4://142.1.174.177:6363 persistency permanent mtu 1450 reliability on
#

nfdc face create udp4://142.1.174.177:6363 persistency permanent mtu 1450 reliability on

iptables -D INPUT -s 142.1.174.177  -j DROP



iptables -A INPUT -s 128.196.203.36  -j DROP

# just in case an on-demand face was created since NFD started, destroy it. 
# This is a temporary fix because an update of a face with mtu change does not currently work.
nfdc face destroy udp4://128.196.203.36:6363

## Test reliability just between ARIZONA and WU
#
#nfdc face create udp4://128.196.203.36:6363 persistency permanent mtu 1450
#

## Use reliability everywhere. Leave it off to LACL until we have them update.
## once LACL gets updated, need to run this again so all nodes go to LACL with reliability turned on
#
#nfdc face create udp4://128.196.203.36:6363 persistency permanent mtu 1450 reliability on
#

nfdc face create udp4://128.196.203.36:6363 persistency permanent mtu 1450 reliability on

iptables -D INPUT -s 128.196.203.36  -j DROP



iptables -A INPUT -s 128.252.185.35  -j DROP

# just in case an on-demand face was created since NFD started, destroy it. 
# This is a temporary fix because an update of a face with mtu change does not currently work.
nfdc face destroy udp4://128.252.185.35:6363

## Test reliability just between ARIZONA and WU
#
#nfdc face create udp4://128.252.185.35:6363 persistency permanent mtu 1450
#

## Use reliability everywhere. Leave it off to LACL until we have them update.
## once LACL gets updated, need to run this again so all nodes go to LACL with reliability turned on
#
#nfdc face create udp4://128.252.185.35:6363 persistency permanent mtu 1450 reliability on
#

nfdc face create udp4://128.252.185.35:6363 persistency permanent mtu 1450 reliability on

iptables -D INPUT -s 128.252.185.35  -j DROP



iptables -A INPUT -s 210.114.89.49  -j DROP

# just in case an on-demand face was created since NFD started, destroy it. 
# This is a temporary fix because an update of a face with mtu change does not currently work.
nfdc face destroy udp4://210.114.89.49:6363

## Test reliability just between ARIZONA and WU
#
#nfdc face create udp4://210.114.89.49:6363 persistency permanent mtu 1450
#

## Use reliability everywhere. Leave it off to LACL until we have them update.
## once LACL gets updated, need to run this again so all nodes go to LACL with reliability turned on
#
#nfdc face create udp4://210.114.89.49:6363 persistency permanent mtu 1450 reliability on
#

nfdc face create udp4://210.114.89.49:6363 persistency permanent mtu 1450 reliability on

iptables -D INPUT -s 210.114.89.49  -j DROP


