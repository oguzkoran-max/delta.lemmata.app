# syntax=docker/dockerfile:1
FROM --platform=linux/amd64 rocker/r-ver:4.5.2@sha256:fd4ccdd3a4a6f7ef805e2daeee2a0fe3bf126bc231f36351223baecf5a595a4c

ARG UV_VERSION=0.11.28
ARG UV_ARCHIVE_SHA256=e490a6464492183c5d4534a5527fb4440f7f2bb2f228162ad7e4afe076dc0224

ENV DEBIAN_FRONTEND=noninteractive \
    UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    UV_PROJECT_ENVIRONMENT=/opt/delta/.venv \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
      ca-certificates \
      curl \
      git \
      libx11-6 \
      libxt6 \
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

COPY VERSION LICENSE README.md pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev

COPY .Rprofile renv.lock ./
COPY renv ./renv
COPY scripts ./scripts
COPY schemas ./schemas
RUN Rscript --vanilla scripts/bootstrap_renv.R

RUN useradd --create-home --shell /usr/sbin/nologin delta \
    && chown -R delta:delta /opt/delta

USER delta

CMD ["/opt/delta/.venv/bin/python", "-c", "import delta_lemmata; print(delta_lemmata.__version__)"]
