FROM python:3.12-slim-bookworm AS metadata-stage
WORKDIR /tmp

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN --mount=type=bind,source=./.git/,target=/tmp/.git/ \
  git describe --tags --exact-match > /tmp/VERSION 2>/dev/null \
  || git rev-parse --short HEAD > /tmp/VERSION \
  && echo "Building version: $(cat /tmp/VERSION)"

FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /bin/uv

WORKDIR /app

ENV TZ=Asia/Shanghai

ENV UV_COMPILE_BYTECODE=1
ENV UV_LOCKED=1
ENV UV_NO_DEV=1
ENV UV_LINK_MODE=copy

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update \
  && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends curl locales fontconfig fonts-noto-color-emoji \
  && localedef -i zh_CN -c -f UTF-8 -A /usr/share/locale/locale.alias zh_CN.UTF-8

COPY pyproject.toml uv.lock README.md ./

RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --all-groups --no-install-project

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  --mount=type=cache,target=/ms-playwright \
  uv run --no-project playwright install --with-deps chromium firefox 

COPY --from=metadata-stage /tmp/VERSION /app/VERSION
COPY main.py entari.yml /app/
COPY miraita /app/miraita/

RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --all-groups

EXPOSE 2310

ENV APP_MODULE=bot:app

HEALTHCHECK --interval=5s --timeout=4s --start-period=180s --retries=5 CMD curl -f http://localhost:${PORT:-2310}/api/v1/health || exit 1

CMD ["uv", "run", "main.py"]
