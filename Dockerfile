# Build Pype docker image
FROM centos:7 AS builder
ARG OPENPYPE_PYTHON_VERSION=3.7.10

LABEL org.opencontainers.image.name="pypeclub/openpype"
LABEL org.opencontainers.image.title="OpenPype Docker Image"
LABEL org.opencontainers.image.url="https://openpype.io/"
LABEL org.opencontainers.image.source="https://github.com/pypeclub/pype"

USER root

RUN yum -y update \
    && yum -y install epel-release centos-release-scl \
    && yum -y install \
        bash \
        which \
        git \
        devtoolset-7-gcc* \
        make \
        cmake \
        curl \
        wget \
        gcc \
        zlib-devel \
        bzip2 \
        bzip2-devel \
        readline-devel \
        sqlite sqlite-devel \
        openssl-devel \
        tk-devel libffi-devel \
        qt5-qtbase-devel \
    && yum clean all

RUN mkdir /opt/openpype
RUN useradd -m pype
RUN chown pype /opt/openpype
USER pype

RUN curl https://pyenv.run | bash
ENV PYTHON_CONFIGURE_OPTS --enable-shared

RUN echo 'export PATH="$HOME/.pyenv/bin:$PATH"'>> $HOME/.bashrc \
    && echo 'eval "$(pyenv init -)"' >> $HOME/.bashrc \
    && echo 'eval "$(pyenv virtualenv-init -)"' >> $HOME/.bashrc
RUN cat $HOME/.bashrc && source $HOME/.bashrc && pyenv install ${OPENPYPE_PYTHON_VERSION}

COPY . /opt/openpype/
USER root
RUN chown -R pype /opt/openpype
RUN chmod +x /opt/openpype/tools/create_env.sh && chmod +x /opt/openpype/tools/build.sh

USER pype

WORKDIR /opt/openpype

RUN cd /opt/openpype \
    && source $HOME/.bashrc \
    && pyenv local ${OPENPYPE_PYTHON_VERSION}

RUN source $HOME/.bashrc \
    && ./tools/create_env.sh

RUN source $HOME/.bashrc \
    && bash ./tools/build.sh
