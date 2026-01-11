#!/bin/bash

# Generate self-signed certificates for local 3-node testbed
# This creates a complete certificate hierarchy for NLSR testing
#
# Each node gets its own separate keychain with only the keys it needs to sign data.
# All nodes share the same trust anchor (root cert) and certificate chain.
#
# Usage: ./scripts/local-certs.sh

set -e

cd "$(dirname "${BASH_SOURCE[0]}")"/..

echo "Generating certificates for local testbed..."

CERT_WORK_DIR=$(pwd)/dist-local-certs
rm -rf "$CERT_WORK_DIR"
mkdir -p "$CERT_WORK_DIR"

# Generate a single function to create node-specific keychain
generate_node_keychain() {
    local NODE_NUM=$1
    local ROUTER_NAME=$2
    
    echo "=== Generating keychain for Node $NODE_NUM ==="
    
    docker run --rm -v "$CERT_WORK_DIR:/certs" -w /certs \
        --user "$(id -u):$(id -g)" \
        --entrypoint /bin/bash \
        ghcr.io/named-data/nfd:20250420 -c "
set -e
export HOME=/certs/node${NODE_NUM}
mkdir -p /certs/node${NODE_NUM}

# Import the root certificate (generated separately)
if [ -f /certs/root.ndncert ]; then
    ndnsec cert-install /certs/root.ndncert 2>/dev/null || true
fi

# Import site certificates for validation
for cert in /certs/node*-site.ndncert; do
    [ -f \"\$cert\" ] && ndnsec cert-install \"\$cert\" 2>/dev/null || true
done

# Import operator certificates for validation
for cert in /certs/node*-operator.ndncert; do
    [ -f \"\$cert\" ] && ndnsec cert-install \"\$cert\" 2>/dev/null || true
done

# Import all router certificates for validation
for cert in /certs/node*-router.ndncert; do
    [ -f \"\$cert\" ] && ndnsec cert-install \"\$cert\" 2>/dev/null || true
done

# Set the default identity to this node's NLSR identity
ndnsec set-default /ndn/local/node${NODE_NUM}/%C1.Router/${ROUTER_NAME}/nlsr 2>/dev/null || true

echo 'Keychain for Node ${NODE_NUM} ready'
"
}

# Step 1: Generate root certificate first
echo "=== Creating Root Certificate ==="
docker run --rm -v "$CERT_WORK_DIR:/certs" -w /certs \
    --user "$(id -u):$(id -g)" \
    --entrypoint /bin/bash \
    ghcr.io/named-data/nfd:20250420 -c '
set -e
export HOME=/certs/root-ca
mkdir -p /certs/root-ca

ndnsec key-gen /ndn > /dev/null
ndnsec cert-dump -i /ndn > /certs/root.ndncert
echo "Root certificate created"
'

# Step 2: Generate all certificates using root CA
echo "=== Creating all node certificates ==="
docker run --rm -v "$CERT_WORK_DIR:/certs" -w /certs \
    --user "$(id -u):$(id -g)" \
    --entrypoint /bin/bash \
    ghcr.io/named-data/nfd:20250420 -c '
set -e
export HOME=/certs/root-ca

# For each node, create site -> operator -> router chain
for NODE_NUM in 1 2 3; do
    ROUTER_NAME="router${NODE_NUM}"
    
    echo "--- Node ${NODE_NUM} ---"
    
    # Site key
    ndnsec key-gen /ndn/local/node${NODE_NUM} > /dev/null
    ndnsec sign-req /ndn/local/node${NODE_NUM} > /tmp/site.req
    ndnsec cert-gen -s /ndn -i "site" /tmp/site.req > /certs/node${NODE_NUM}-site.ndncert
    ndnsec cert-install /certs/node${NODE_NUM}-site.ndncert
    
    # Operator key
    ndnsec key-gen "/ndn/local/node${NODE_NUM}/%C1.Operator/op" > /dev/null
    ndnsec sign-req "/ndn/local/node${NODE_NUM}/%C1.Operator/op" > /tmp/op.req
    ndnsec cert-gen -s /ndn/local/node${NODE_NUM} -i "operator" /tmp/op.req > /certs/node${NODE_NUM}-operator.ndncert
    ndnsec cert-install /certs/node${NODE_NUM}-operator.ndncert
    
    # Router key (for NLSR)
    ndnsec key-gen "/ndn/local/node${NODE_NUM}/%C1.Router/${ROUTER_NAME}/nlsr" > /dev/null
    ndnsec sign-req "/ndn/local/node${NODE_NUM}/%C1.Router/${ROUTER_NAME}/nlsr" > /tmp/router.req
    ndnsec cert-gen -s "/ndn/local/node${NODE_NUM}/%C1.Operator/op" -i "router" /tmp/router.req > /certs/node${NODE_NUM}-router.ndncert
    ndnsec cert-install /certs/node${NODE_NUM}-router.ndncert
done

# Copy the complete keychain for each node (they all need all keys for validation + their own for signing)
for NODE_NUM in 1 2 3; do
    mkdir -p /certs/node${NODE_NUM}
    cp -r /certs/root-ca/.ndn /certs/node${NODE_NUM}/.ndn
done

echo "All certificates created"
'

# Step 3: Set default identity for each node
echo "=== Setting default identities ==="
for NODE_NUM in 1 2 3; do
    ROUTER_NAME="router${NODE_NUM}"
    docker run --rm -v "$CERT_WORK_DIR:/certs" -w /certs \
        --user "$(id -u):$(id -g)" \
        --entrypoint /bin/bash \
        ghcr.io/named-data/nfd:20250420 -c "
set -e
export HOME=/certs/node${NODE_NUM}
ndnsec set-default /ndn/local/node${NODE_NUM}/%C1.Router/${ROUTER_NAME}/nlsr
echo 'Node ${NODE_NUM} default identity set'
"
done

echo ""
echo "=== Distributing certificates to nodes ==="

# Copy root cert as trust anchor for local testing
mkdir -p anchors-local
cp "$CERT_WORK_DIR/root.ndncert" anchors-local/local-root.ndncert

# Setup node1
mkdir -p dist-local1/nlsr/state
cp "$CERT_WORK_DIR/node1-operator.ndncert" dist-local1/nlsr/operator.cert
cp "$CERT_WORK_DIR/node1-router.ndncert" dist-local1/nlsr/router.cert
rm -rf dist-local1/nlsr/.ndn
cp -r "$CERT_WORK_DIR/node1/.ndn" dist-local1/nlsr/.ndn

# Setup node2  
mkdir -p dist-local2/nlsr/state
cp "$CERT_WORK_DIR/node2-operator.ndncert" dist-local2/nlsr/operator.cert
cp "$CERT_WORK_DIR/node2-router.ndncert" dist-local2/nlsr/router.cert
rm -rf dist-local2/nlsr/.ndn
cp -r "$CERT_WORK_DIR/node2/.ndn" dist-local2/nlsr/.ndn

# Setup node3
mkdir -p dist-local3/nlsr/state
cp "$CERT_WORK_DIR/node3-operator.ndncert" dist-local3/nlsr/operator.cert
cp "$CERT_WORK_DIR/node3-router.ndncert" dist-local3/nlsr/router.cert
rm -rf dist-local3/nlsr/.ndn
cp -r "$CERT_WORK_DIR/node3/.ndn" dist-local3/nlsr/.ndn

echo ""
echo "=== Certificate generation complete! ==="
echo ""
echo "Trust anchor: anchors-local/local-root.ndncert"
echo "Node 1 certs: dist-local1/nlsr/{operator.cert,router.cert,.ndn/}"
echo "Node 2 certs: dist-local2/nlsr/{operator.cert,router.cert,.ndn/}"
echo "Node 3 certs: dist-local3/nlsr/{operator.cert,router.cert,.ndn/}"
echo ""
echo "To start the testbed:"
echo "  docker compose -f docker-compose.local.yml down"
echo "  docker compose -f docker-compose.local.yml up -d"
