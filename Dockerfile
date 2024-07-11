##############
### Flyway
##############

FROM flyway/flyway:10-alpine as flyway

USER flyway
# Copy the flyway files to the container
COPY ./database/flyway /flyway
ENTRYPOINT ["/flyway/entrypoint.bash"]

USER root

RUN apk add --no-cache tzdata
ENV TZ=America/New_York
RUN apk add --no-cache postgresql-client

##############
### Builder
##############
FROM python:3.12-slim as builder

USER root
WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt -qq update && apt -qq -y --no-install-recommends install git

RUN pip install poetry && \
    poetry self update && \
    poetry self add "poetry-dynamic-versioning[plugin]"

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

COPY . /app/

RUN --mount=type=cache,target=$POETRY_CACHE_DIR \
    chown -R root:root /app && \
    poetry --no-interaction install && \
    poetry --no-interaction build -f sdist

##############
### Runtime
##############
FROM python:3.12-slim as runtime

USER root

COPY --from=builder /app/dist/*.tar.gz .

RUN touch /usr/local/bin/volleyball-uploader-oauth2.json

RUN pip install *.tar.gz && rm *.tar.gz
