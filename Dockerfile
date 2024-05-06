# syntax=docker/dockerfile:1

ARG NDN_CXX_VERSION=latest

FROM python:3-alpine AS testbed-master

RUN <<EOF
    apk add docker-cli docker-cli-compose
    pip install --no-cache-dir --disable-pip-version-check \
        PyYAML \
        python-ndn==0.4.2 \
        Jinja2==3.1.4
EOF

VOLUME /repo
WORKDIR /repo


FROM ghcr.io/named-data/ndn-cxx-runtime:${NDN_CXX_VERSION} AS http-ca-server

RUN <<EOF
    apt-get install -Uy --no-install-recommends \
        python3 \
        python3-pip
    apt-get distclean

    pip install --no-cache-dir --disable-pip-version-check --break-system-packages \
        PyYAML \
        python-ndn==0.4.2
EOF

COPY http-ca-server.py /app/http-ca-server.py

ENV HOME=/config
VOLUME /config

EXPOSE 8777

ENTRYPOINT ["/app/http-ca-server.py"]
CMD ["/config/http-ca-server.yml"]