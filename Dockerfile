# Build Pype docker image
FROM centos:7 AS system_builder
ARG OPENPYPE_PYTHON_VERSION=3.7.10

LABEL org.opencontainers.image.name="pypeclub/openpype"
LABEL org.opencontainers.image.title="OpenPype Docker Image"
LABEL org.opencontainers.image.url="https://openpype.io/"
LABEL org.opencontainers.image.source="https://github.com/pypeclub/pype"

USER root

# update base
RUN yum -y install deltarpm \
    && yum -y update \
    && yum clean all

# add tools we need
RUN yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm \
    && yum -y install centos-release-scl \
    && yum -y install \
        bash \
        which \
        git \
        devtoolset-7-gcc* \
	gcc-c++ \
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
	autoconf \
	automake \
    && yum clean all

# we need to build our own patchelf
WORKDIR /temp-patchelf
RUN git clone https://github.com/NixOS/patchelf.git . \
    && source scl_source enable devtoolset-7 \
    && ./bootstrap.sh \
    && ./configure \
    && make \
    && make install
	

RUN curl https://pyenv.run | bash
ENV PYTHON_CONFIGURE_OPTS --enable-shared

RUN echo 'export PATH="$HOME/.pyenv/bin:$PATH"'>> $HOME/.bashrc \
    && echo 'eval "$(pyenv init -)"' >> $HOME/.bashrc \
    && echo 'eval "$(pyenv virtualenv-init -)"' >> $HOME/.bashrc \
    && echo 'eval "$(pyenv init --path)"' >> $HOME/.bashrc \
    && source $HOME/.bashrc \
    && pyenv install ${OPENPYPE_PYTHON_VERSION}

WORKDIR /opt/openpype
COPY . /opt/openpype/
RUN rm -rf /opt/openpype/.poetry || echo "No Poetry installed yet." \
    && chmod +x /opt/openpype/tools/create_env.sh \
    && chmod +x /opt/openpype/tools/build.sh \
    && source $HOME/.bashrc \
    && pyenv local ${OPENPYPE_PYTHON_VERSION}

RUN source $HOME/.bashrc \
    && ./tools/create_env.sh \
    && source $HOME/.bashrc \
    && ./tools/fetch_thirdparty_libs.sh

RUN source $HOME/.bashrc \
    && bash ./tools/build.sh \
    && cp /usr/lib64/libffi* ./build/exe.linux-x86_64-3.7/lib \
    && cp /usr/lib64/libssl* ./build/exe.linux-x86_64-3.7/lib \
    && cp /usr/lib64/libcrypto* ./build/exe.linux-x86_64-3.7/lib
