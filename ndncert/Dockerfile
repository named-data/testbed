FROM ghcr.io/named-data/ndn-cxx:latest as builder

COPY . /ndncert

RUN cd ndncert && \
    ./waf configure && \
    ./waf && \
    ./waf install && \
    ldconfig

ENTRYPOINT [ "/usr/local/bin/ndncert-ca-server" ]
# CMD [ "ndncert-client" ]