FROM ghcr.io/named-data/ndn-cxx:latest as builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ca-certificates \
    && echo "deb [trusted=yes] https://nfd-nightly-apt.ndn.today/debian bullseye main" > /etc/apt/sources.list.d/nfd-nightly.list \
    && apt-get install -y --no-install-recommends ndn-6tools \
    && rm -rf /var/lib/apt/lists/*

CMD [ "ls" ]