# syntax=docker/dockerfile:1

ARG NDN_CXX_VERSION=latest
FROM ghcr.io/named-data/ndn-cxx-runtime:${NDN_CXX_VERSION} AS http-ca-server

RUN apt-get install -Uy --no-install-recommends \
        python3 \
        python3-pip \
    && apt-get distclean \
    && pip install --no-cache-dir --disable-pip-version-check --break-system-packages \
        pyyaml \
        python-ndn

COPY http-ca-server.py /app/http-ca-server.py

ENV HOME=/config
VOLUME /config

EXPOSE 8777

ENTRYPOINT ["/app/http-ca-server.py"]
CMD ["/config/http-ca-server.yml"]