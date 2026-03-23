# nlsr.Dockerfile - Build NLSR with Gerrit patch 7818 applied
# Patch 7818: Recover lost LSA seqNo from network via sync
#
# Build and push to your own ghcr.io registry:
#   docker build -t ghcr.io/<username>/nlsr:patch-7818 -f nlsr.Dockerfile .
#   docker push ghcr.io/<username>/nlsr:patch-7818

# Stage 1: Build ndn-cxx, psync, and NLSR from source
FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    ccache \
    python3 \
    python3-dev \
    python3-setuptools \
    pkg-config \
    libboost-dev \
    libboost-filesystem-dev \
    libboost-system-dev \
    libboost-chrono-dev \
    libboost-thread-dev \
    libboost-program-options-dev \
    libboost-date-time-dev \
    libboost-log-dev \
    libboost-stacktrace-dev \
    libboost-iostreams-dev \
    libsqlite3-dev \
    libspdlog-dev \
    libssl-dev \
    libpcap-dev \
    protobuf-compiler \
    libprotobuf-dev \
    googletest \
    libgtest-dev \
    && rm -rf /var/lib/apt/lists/*

# Build ndn-cxx from source first (psync depends on it)
WORKDIR /build
RUN git clone --depth 1 --branch master https://github.com/named-data/ndn-cxx.git ndn-cxx
WORKDIR /build/ndn-cxx
RUN ./waf configure --prefix=/usr/local && ./waf build -j$(nproc) && ./waf install
RUN ldconfig

# Build psync from source (uses waf, depends on ndn-cxx)
WORKDIR /build
RUN git clone --depth 1 --branch master https://github.com/named-data/psync.git psync
WORKDIR /build/psync
RUN ./waf configure --prefix=/usr/local && ./waf build -j$(nproc) && ./waf install
RUN ldconfig

# Clone and build NLSR with patch
WORKDIR /build
RUN git clone --depth 1 --branch master https://github.com/named-data/NLSR.git nlsr
WORKDIR /build/nlsr

# Fetch patch 7818 from Gerrit
# Change ref if a newer revision is available (e.g., /2, /3, etc.)
ARG NLSR_PATCH_REF=refs/changes/18/7818/1
RUN git fetch https://gerrit.named-data.net/NLSR.git ${NLSR_PATCH_REF} && \
    git checkout FETCH_HEAD

# Build NLSR using waf
RUN ./waf configure --prefix=/usr/local && ./waf build -j$(nproc) && ./waf install

# Stage 2: Runtime image
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Runtime dependencies
RUN apt-get update && apt-get install -y \
    libboost-filesystem-dev \
    libboost-system-dev \
    libboost-chrono-dev \
    libboost-thread-dev \
    libboost-program-options-dev \
    libboost-date-time-dev \
    libsqlite3-0 \
    libspdlog-dev \
    libssl3 \
    libpcap0.8 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy built artifacts from builder
COPY --from=builder /usr/local/lib /usr/local/lib
COPY --from=builder /usr/local/include /usr/local/include
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/etc /usr/local/etc

RUN ldconfig

LABEL org.opencontainers.image.source=https://github.com/named-data/NLSR
LABEL org.opencontainers.image.description="NLSR with patch 7818 (LSA seqNo recovery via sync)"
