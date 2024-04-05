FROM ghcr.io/named-data/ndn-cxx:latest as builder

COPY . /ndn6

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ca-certificates gdb git \
    && cd ndn6 \
    && make \
    && make install \
    && ldconfig \
    # get list of dependencies
    && mkdir -p /shlibdeps/debian && cd /shlibdeps && touch debian/control \
    && dpkg-shlibdeps --ignore-missing-info /usr/lib/libndn-cxx.so* /ndn6/facemon /ndn6/file-server \
    /ndn6/prefix-allocate /ndn6/prefix-proxy /ndn6/register-prefix-cmd \
    /ndn6/register-prefix-remote /ndn6/serve-certs /ndn6/unix-time-service \
    && sed -n '/^shlibs:Depends=/ s|shlibs:Depends=||p' debian/substvars | sed -e 's|,||g' -e 's| ([^)]*)||g' > /deps.txt

# use same base distro version as named-data/ndn-cxx
FROM debian:bookworm

COPY --from=builder /deps.txt /
RUN apt-get update \
    && apt-get install -y --no-install-recommends $(cat /deps.txt) \
    && rm -rf /var/lib/apt/lists/* /deps.txt

RUN ls /usr/local/lib
COPY --from=builder /usr/lib/libndn-cxx.so* /usr/lib/
COPY --from=builder /ndn6 /usr/bin/ndn6

ENV HOME=/config

VOLUME /config
VOLUME /run/nfd

# This line doesn't work because you need to specify the certificate files to run from.
# Needs to have a *.ndncert file as an argument.
# ENTRYPOINT [ "/usr/bin/ndn6/serve-certs" ]