# syntax=docker/dockerfile:1

ARG UV_VERSION=0.10.7
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

COPY --from=uv /uv /uvx /usr/local/bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    VIRTUAL_ENV=/opt/venv \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    UV_LINK_MODE=copy \
    TZ=Asia/Shanghai \
    LANG=zh_CN.UTF-8 \
    LC_ALL=zh_CN.UTF-8 \
    PATH="/opt/venv/bin:${PATH}"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      fontconfig \
      fonts-noto-color-emoji \
      locales \
    && localedef -i zh_CN -c -f UTF-8 \
      -A /usr/share/locale/locale.alias zh_CN.UTF-8 \
    && mkdir -p /opt/venv /ms-playwright \
    && chown -R vscode:vscode /opt/venv /ms-playwright

WORKDIR /tmp/miraita
COPY --chown=vscode:vscode pyproject.toml uv.lock README.md ./

USER vscode
RUN --mount=type=cache,target=/home/vscode/.cache/uv,uid=1000,gid=1000 \
    uv sync --all-groups --all-extras --locked --no-install-project

USER root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    playwright install --with-deps chromium \
    && chown -R vscode:vscode /opt/venv /ms-playwright \
    && rm -rf /tmp/miraita

USER vscode
