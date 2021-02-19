FROM python:3.7-slim-stretch
RUN pip install --upgrade pip

ARG DOCKERHUB_REGISTRY="pyaiot"
# Avoid building rust for cryptography
ARG CRYPTOGRAPHY_DONT_BUILD_RUST=1

LABEL maintainer="alexandre.abadie@inria.fr"

ARG GIT_REMOTE="pyaiot"
# gcc and git need to be present for next install
RUN apt-get update && apt-get install -y git gcc \
    && apt-get autoremove && apt-get autoclean
RUN \
    echo 'Update the package index files to latest available versions' >&2 && \
    apt-get update && \
    echo 'Installing static test tools' >&2 && \
    apt-get -y --no-install-recommends install \
        libffi-dev \
        libssl-dev \
        && \
    echo 'Cleaning up installation files' >&2 && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
RUN pip3 install git+https://github.com/${GIT_REMOTE}/pyaiot.git

RUN aiot-generate-keys
