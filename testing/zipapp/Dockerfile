FROM ubuntu:bionic
RUN : \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-distutils \
        python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=C.UTF-8 PATH=/venv/bin:$PATH
RUN : \
    && python3.6 -mvenv /venv \
    && pip install --no-cache-dir pip setuptools wheel no-manylinux --upgrade
