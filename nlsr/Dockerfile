FROM ghcr.io/named-data/ndn-cxx:latest as builder

RUN git clone --depth 1 https://github.com/named-data/PSync \
    && cd PSync \
    && ./waf configure \
    && ./waf \
    && ./waf install \
    && ldconfig \
    && cd .. \
    && rm -rf PSync

COPY . /nlsr

RUN cd nlsr && \
    ./waf configure && \
    ./waf && \
    ./waf install \
    # get list of dependencies
    && mkdir -p /shlibdeps/debian && cd /shlibdeps && touch debian/control \
    && dpkg-shlibdeps --ignore-missing-info /usr/lib/libndn-cxx.so* /usr/local/lib/libPSync.so* /usr/local/bin/nlsr \
    && sed -n '/^shlibs:Depends=/ s|shlibs:Depends=||p' debian/substvars | sed -e 's|,||g' -e 's| ([^)]*)||g' > /deps.txt

# use same base distro version as named-data/ndn-cxx
FROM debian:bookworm

COPY --from=builder /deps.txt /
RUN apt-get update \
    && apt-get install -y --no-install-recommends $(cat /deps.txt) \
    && rm -rf /var/lib/apt/lists/* /deps.txt

RUN ls /usr/local/lib
COPY --from=builder /usr/lib/libndn-cxx.so* /usr/local/lib/libPSync.so* /usr/lib/
COPY --from=builder /usr/local/bin/nlsr /usr/local/bin/nlsrc /usr/bin/
COPY --from=builder /usr/local/etc/ndn/nlsr.conf.sample /config/nlsr.conf

ENV HOME=/config

VOLUME /config
VOLUME /run/nfd

ENTRYPOINT ["/usr/bin/nlsr"]
CMD ["-f", "/config/nlsr.conf"]
