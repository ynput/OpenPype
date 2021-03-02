FROM python:3.7-alpine AS builder
WORKDIR /pype
COPY . .
RUN apk add --no-cache gcc cmake bash curl binutils tar
RUN bash ./tools/create_env.sh
RUN bash ./tools/build.sh

FROM alpine:3.13 AS executor
RUN apk add --no-cache bash zlib
COPY --from=builder build/exe.linux-x86_64-3.7 /test/
USER nobody:nobody
ENTRYPOINT ["/test/pype_console"]