# Build Pype docker image
FROM debian:bookworm-slim AS builder
ARG OPENPYPE_PYTHON_VERSION=3.7.12

LABEL maintainer="info@openpype.io"
LABEL description="Docker Image to build and run OpenPype"
LABEL org.opencontainers.image.name="pypeclub/openpype"
LABEL org.opencontainers.image.title="OpenPype Docker Image"
LABEL org.opencontainers.image.url="https://openpype.io/"
LABEL org.opencontainers.image.source="https://github.com/pypeclub/pype"

USER root

ARG DEBIAN_FRONTEND=noninteractive

# update base
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        bash \
        git \
        cmake \
        make \
        curl \
        wget \
        build-essential \
        checkinstall \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        llvm \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libffi-dev \
        liblzma-dev \
        patchelf

SHELL ["/bin/bash", "-c"]

RUN mkdir /opt/openpype

RUN curl https://pyenv.run | bash \
    && echo 'export PATH="$HOME/.pyenv/bin:$PATH"'>> $HOME/.bashrc \
    && echo 'eval "$(pyenv init -)"' >> $HOME/.bashrc \
    && echo 'eval "$(pyenv virtualenv-init -)"' >> $HOME/.bashrc \
    && echo 'eval "$(pyenv init --path)"' >> $HOME/.bashrc \
    && source $HOME/.bashrc && pyenv install ${OPENPYPE_PYTHON_VERSION}

COPY . /opt/openpype/

RUN chmod +x /opt/openpype/tools/create_env.sh && chmod +x /opt/openpype/tools/build.sh

WORKDIR /opt/openpype

RUN cd /opt/openpype \
    && source $HOME/.bashrc \
    && pyenv local ${OPENPYPE_PYTHON_VERSION}

RUN source $HOME/.bashrc \
    && ./tools/create_env.sh \
    && ./tools/fetch_thirdparty_libs.sh

RUN source $HOME/.bashrc \
    && bash ./tools/build.sh
