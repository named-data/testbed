FROM ghcr.io/named-data/ndn-cxx:latest as builder

COPY . /ndncert

RUN cd ndncert && \
    ./waf configure && \
    ./waf && \
    ./waf install && \
    ldconfig \
    # get list of dependencies
    && mkdir -p /shlibdeps/debian && cd /shlibdeps && touch debian/control \
    && dpkg-shlibdeps --ignore-missing-info /usr/lib/libndn-cxx.so* /usr/local/bin/ndncert-ca-server \
    && sed -n '/^shlibs:Depends=/ s|shlibs:Depends=||p' debian/substvars | sed -e 's|,||g' -e 's| ([^)]*)||g' > /deps.txt

# use same base distro version as named-data/ndn-cxx
FROM debian:bookworm

COPY --from=builder /deps.txt /
RUN apt-get update \
    && apt-get install -y --no-install-recommends $(cat /deps.txt) \
    && rm -rf /var/lib/apt/lists/* /deps.txt

RUN ls /usr/local/lib
COPY --from=builder /usr/lib/libndn-cxx.so* /usr/lib/
COPY --from=builder /usr/local/bin/ndncert-ca-server /usr/local/bin/ndncert-ca-server /usr/bin/
COPY --from=builder /ndncert/ca.conf.sample /config/ca.conf.sample
COPY --from=builder /ndncert/client.conf.sample /config/client.conf.sample

ENV HOME=/config

VOLUME /config
VOLUME /run/nfd

ENTRYPOINT [ "/usr/bin/ndncert-ca-server" ]
# CMD [ "ndncert-client" ]

