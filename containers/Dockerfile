# syntax=docker/dockerfile:1
FROM --platform=linux/amd64 rocker/r-ver:4.5.2@sha256:fd4ccdd3a4a6f7ef805e2daeee2a0fe3bf126bc231f36351223baecf5a595a4c

ARG UV_VERSION=0.11.28
ARG UV_ARCHIVE_SHA256=e490a6464492183c5d4534a5527fb4440f7f2bb2f228162ad7e4afe076dc0224
ARG DELTA_BUILD_ID=development

LABEL org.opencontainers.image.title="Delta" \
      org.opencontainers.image.source="https://github.com/oguzkoran-max/delta.lemmata.app" \
      org.opencontainers.image.revision="${DELTA_BUILD_ID}" \
      org.opencontainers.image.licenses="MIT"

ENV DEBIAN_FRONTEND=noninteractive \
    RENV_PATHS_CACHE=/opt/renv/cache \
    UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    UV_PROJECT_ENVIRONMENT=/opt/delta/.venv \
    TMPDIR=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
      ca-certificates \
      curl \
      git \
      libx11-6 \
      libxt6 \
      procps \
      tcl8.6 \
      tk8.6 \
      xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN curl --fail --location --silent --show-error \
      "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz" \
      --output /tmp/uv.tar.gz \
    && echo "${UV_ARCHIVE_SHA256}  /tmp/uv.tar.gz" | sha256sum --check --strict \
    && tar --extract --gzip --file /tmp/uv.tar.gz --directory /tmp \
    && install -m 0755 /tmp/uv-x86_64-unknown-linux-gnu/uv /usr/local/bin/uv \
    && install -m 0755 /tmp/uv-x86_64-unknown-linux-gnu/uvx /usr/local/bin/uvx \
    && rm -rf /tmp/uv.tar.gz /tmp/uv-x86_64-unknown-linux-gnu

RUN uv python install 3.13.9

WORKDIR /opt/delta

COPY VERSION LICENSE README.md app.py pyproject.toml uv.lock ./
COPY .streamlit ./.streamlit
COPY src ./src
RUN uv sync --frozen --no-dev

COPY .Rprofile renv.lock ./
COPY renv ./renv
COPY scripts ./scripts
COPY schemas ./schemas
RUN Rscript --vanilla scripts/bootstrap_renv.R \
    && chmod -R a+rX /opt/renv/cache

RUN groupadd --gid 10001 delta \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin delta \
    && chown -R delta:delta /opt/delta

ENV HOME=/home/delta

USER delta

RUN Rscript --vanilla -e 'setwd("/opt/delta"); source("renv/activate.R"); stopifnot(requireNamespace("jsonlite", quietly = TRUE)); stopifnot(requireNamespace("stylo", quietly = TRUE)); stopifnot(as.character(packageVersion("jsonlite")) == "2.0.0"); stopifnot(as.character(packageVersion("stylo")) == "0.7.71"); cat("r-runtime-namespace-ok\n")'

RUN --mount=type=bind,source=tests/fixtures/stylo/p006-whole-text-v2,target=/opt/delta/tests/fixtures/stylo/p006-whole-text-v2,readonly \
    --mount=type=bind,source=provenance/evidence/P006/oracle-v2,target=/opt/delta/provenance/evidence/P006/oracle-v2,readonly \
    /bin/sh -c '/opt/delta/.venv/bin/python scripts/validate_p006_worker_parity.py --require-reference-session \
      && /opt/delta/.venv/bin/python scripts/validate_p006_scientific_handoff.py'

EXPOSE 8501

HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=6 \
  CMD ["/opt/delta/.venv/bin/python", "-c", "import urllib.request; response = urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=2); assert response.status == 200 and response.read(16).strip() == b'ok'"]

CMD ["/opt/delta/.venv/bin/streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
