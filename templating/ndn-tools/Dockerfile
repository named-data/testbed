FROM ghcr.io/named-data/ndn-cxx-build:latest as builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . /ndn-tools

RUN cd ndn-tools && \
    ./waf configure && \
    ./waf && \
    ./waf install \
    # get list of dependencies
    && mkdir -p /shlibdeps/debian && cd /shlibdeps && touch debian/control \
    && dpkg-shlibdeps --ignore-missing-info /usr/lib/libndn-cxx.so* /usr/local/bin/ndnpingserver /usr/local/bin/ndnping \
    && sed -n '/^shlibs:Depends=/ s|shlibs:Depends=||p' debian/substvars | sed -e 's|,||g' -e 's| ([^)]*)||g' > /deps.txt

# use same base distro version as named-data/ndn-cxx
FROM ghcr.io/named-data/ndn-cxx-runtime:latest

COPY --from=builder /deps.txt /
RUN apt-get update \
    && apt-get install -y --no-install-recommends $(cat /deps.txt) \
    && rm -rf /var/lib/apt/lists/* /deps.txt

RUN ls /usr/local/lib
COPY --from=builder /usr/lib/libndn-cxx.so* /usr/lib/
COPY --from=builder /usr/local/bin/ndnpingserver /usr/bin/
COPY --from=builder /usr/local/bin/ndnping /usr/bin/
COPY --from=builder /ndn-tools/entrypoint.sh ./

ENV HOME=/config

VOLUME /config
VOLUME /run/nfd

ENTRYPOINT [ "/bin/sh" ]
CMD [ "./entrypoint.sh" ]