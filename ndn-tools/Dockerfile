FROM ghcr.io/named-data/ndn-cxx:latest as builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . /ndn-tools

RUN cd ndn-tools && \
    ./waf configure && \
    ./waf && \
    ./waf install

ENTRYPOINT [ "/usr/local/bin/ndnpingserver" ]