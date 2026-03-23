# nlsr.Dockerfile - Build NLSR with Gerrit patch 7818 applied
# Patch 7818: Recover lost LSA seqNo from network via sync
#
# Uses Named Data's base images for proper library paths
# Build and push to your own ghcr.io registry:
#   docker build -t ghcr.io/<username>/nlsr:patch-7818 -f nlsr.Dockerfile .
#   docker push ghcr.io/<username>/nlsr:patch-7818

# Stage 1: Build using Named Data's build environment
FROM ghcr.io/named-data/ndn-cxx-build AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Ensure SSL certs are available for git and install boost iostreams
RUN apt-get update && apt-get install -y ca-certificates libboost-iostreams-dev && rm -rf /var/lib/apt/lists/*

# Build psync from source (psync is not in the base image)
WORKDIR /build
RUN git clone --depth 1 --branch master https://github.com/named-data/psync.git psync
WORKDIR /build/psync
RUN ./waf configure --prefix=/usr --libdir=/usr/lib && \
    ./waf build -j$(nproc) && ./waf install

# Clone NLSR and apply patch
WORKDIR /build
RUN git clone --depth 1 --branch master https://github.com/named-data/NLSR.git nlsr
WORKDIR /build/nlsr

# Fetch patch 7818 from Gerrit
# Use latest revision (change ref if needed: /1, /2, ..., /6)
ARG NLSR_PATCH_REF=refs/changes/18/7818/6
RUN git fetch https://gerrit.named-data.net/NLSR.git ${NLSR_PATCH_REF} && \
    git checkout FETCH_HEAD

# Build NLSR using waf with --with-psync to find psync
RUN ./waf configure --prefix=/usr --libdir=/usr/lib --with-psync && \
    ./waf build -j$(nproc) && ./waf install

# Stage 2: Runtime image using Named Data's runtime base
FROM ghcr.io/named-data/ndn-cxx-runtime

ENV DEBIAN_FRONTEND=noninteractive

# Runtime dependencies for NLSR
RUN apt-get update && apt-get install -y \
    libsqlite3-0 \
    libpcap0.8 \
    libboost-iostreams1.83.0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy built NLSR and psync artifacts from builder
COPY --from=builder /usr/bin/nlsr /usr/bin/nlsr
COPY --from=builder /usr/bin/nlsrc /usr/bin/nlsrc
COPY --from=builder /usr/lib/libPSync.so* /usr/lib/

# Default entrypoint matches original image
ENTRYPOINT ["/usr/bin/nlsr"]
CMD ["-f", "/config/nlsr.conf"]

LABEL org.opencontainers.image.source=https://github.com/named-data/NLSR
LABEL org.opencontainers.image.description="NLSR with patch 7818 (LSA seqNo recovery via sync)"