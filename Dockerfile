# Build Pype docker image
FROM ubuntu:focal AS builder
ARG PYTHON_VERSION=3.9.12
ARG BUILD_DATE
ARG VERSION

LABEL maintainer="info@openpype.io"
LABEL description="Docker Image to build and run AYON under Ubuntu 20.04"
LABEL org.opencontainers.image.name="ynput/desktop"
LABEL org.opencontainers.image.title="AYON Desktop Docker Image"
LABEL org.opencontainers.image.url="https://ayon.ynput.io/"
LABEL org.opencontainers.image.source="https://github.com/ynput/OpenPype"
LABEL org.opencontainers.image.documentation="https://ayon.ynput.io"
LABEL org.opencontainers.image.created=$BUILD_DATE
LABEL org.opencontainers.image.version=$VERSION

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


RUN mkdir /opt/ayon

# download and install pyenv
RUN curl https://pyenv.run | bash \
    && echo 'export PATH="$HOME/.pyenv/bin:$PATH"'>> $HOME/init_pyenv.sh \
    && echo 'eval "$(pyenv init -)"' >> $HOME/init_pyenv.sh \
    && echo 'eval "$(pyenv virtualenv-init -)"' >> $HOME/init_pyenv.sh \
    && echo 'eval "$(pyenv init --path)"' >> $HOME/init_pyenv.sh

# install python with pyenv
RUN source $HOME/init_pyenv.sh \
    && pyenv install ${PYTHON_VERSION}

COPY . /opt/ayon/

RUN chmod +x /opt/ayon/tools/create_env.sh && chmod +x /opt/ayon/tools/build.sh

WORKDIR /opt/ayon

# set local python version
RUN cd /opt/ayon \
    && source $HOME/init_pyenv.sh \
    && pyenv local ${PYTHON_VERSION}

# fetch third party tools/libraries
RUN source $HOME/init_pyenv.sh \
    && ./tools/create_env.sh \
    && ./tools/fetch_thirdparty_libs.sh

# build ayon desktop
RUN source $HOME/init_pyenv.sh \
    && bash ./tools/build.sh
