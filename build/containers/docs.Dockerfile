# syntax=docker/dockerfile:1.7
FROM python:3.12-alpine AS build

WORKDIR /src
COPY docs/requirements.txt /tmp/docs-requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/docs-requirements.txt

COPY . .
RUN sphinx-build -W --keep-going -b html docs docs/_build/html

FROM scratch AS export
COPY --from=build /src/docs/_build/html/ /
