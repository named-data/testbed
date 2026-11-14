# syntax=docker/dockerfile:1

ARG NDN_CXX_VERSION=latest

FROM ghcr.io/named-data/ndn-cxx-runtime:${NDN_CXX_VERSION} AS testbed-master

RUN <<EOF
    set -eux

    apt-get install -Uy --no-install-recommends ca-certificates curl
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get install -Uy --no-install-recommends \
        git \
        busybox \
        python3 \
        python3-pip \
        docker-ce-cli \
        docker-compose-plugin
    apt-get distclean

    pip install --no-cache-dir --disable-pip-version-check --break-system-packages \
        jinja2==3.1.6 \
        python-ndn==0.5.2 \
        pyyaml==6.0.3
EOF

VOLUME /testbed
WORKDIR /testbed


# NDNd is scratch-based; add a shell for rendered tool entrypoints.
FROM busybox:1.37.0-musl@sha256:f6a95d611e0a8780fabdb2aec43e31275b2720dfefa3e41b16835bfc42454478 AS ndnd-tools-shell

FROM golang:1.24 AS ndnd-tools-build

# The ping-prefix fix is isolated from the deployed router/repository images.
ADD --keep-git-dir=true https://github.com/markverick/ndnd.git#f9c34574aa0dc7d295fa28bacd8b3060c650df15 /src
WORKDIR /src
RUN make

FROM ghcr.io/named-data/ndnd:dv2-staging@sha256:aba4d409d0f3ed2a7b134bd5d0ade0e0c9c37ad55e69254951c306f961b36d5b AS testbed-ndnd-tools

COPY --from=ndnd-tools-build /src/ndnd /ndnd
COPY --from=ndnd-tools-shell /bin/busybox /bin/sh


FROM caddy:2-alpine AS testbed-caddy

ADD --unpack https://nfd-status-page.ndn.today/NDNts-NFD-status-page.txz /srv/n
