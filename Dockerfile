##############
### Flyway
##############

FROM flyway/flyway:10-alpine AS flyway

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
FROM python:3.12-slim AS builder

USER root
WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt -qq update && apt -qq -y --no-install-recommends install git

# Build uv app with dependencies installed
ENV UV_CACHE_DIR=/tmp/uv_cache

COPY . /app/

RUN pip install --upgrade pip && \
    pip install uv && \
    uv sync --frozen

RUN --mount=type=cache,target=$UV_CACHE_DIR \
    chown -R root:root /app && \
    uv build --upgrade --sdist

##############
### Runtime
##############
FROM python:3.12-slim AS runtime

USER root

COPY --from=builder /app/dist/*.tar.gz .

RUN touch /usr/local/bin/uploader-oauth2.json

RUN pip install *.tar.gz && rm *.tar.gz

ENTRYPOINT ["uploader"]