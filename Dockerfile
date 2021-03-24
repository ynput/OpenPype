FROM python:3.7-stretch AS builder
WORKDIR /pype
COPY poetry.toml .
COPY pyproject.toml .
# COPY poetry.lock .
COPY /tools tools/
# RUN apt purge --auto-remove cmake \
#    && mkdir /temp \
#    && cd /temp \
# 	 && curl https://cmake.org/files/v3.19/cmake-3.19.7.tar.gz > cmake.tar.gz\
#    && tar -xzvf cmake.tar.gz \
#    && cd cmake-3.19.7/ \
#    && ./bootstrap \
#    && make -j4 \
#    && make install

RUN apt-get install -y --no-install-recommends git
RUN bash ./tools/create_env.sh

COPY . .
RUN bash ./tools/build.sh

FROM debian:stretch AS executor
RUN apt-get install -y --no-install-recommends zlib
COPY --from=builder build/exe.linux-x86_64-3.7 /test/
USER nobody:nobody
ENTRYPOINT ["/test/pype_console --help"]
