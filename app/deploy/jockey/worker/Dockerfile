# dockerfile for worker (in the root dir because Railway makes us)

FROM python:3.12-slim-bookworm

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    awscli \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

#COPY jockey/pyproject.toml /app/
COPY jockey /app/jockey

RUN uv pip install --system -e jockey

# Create non-root user
RUN useradd --create-home --shell /bin/bash worker
RUN chown -R worker:worker /app
USER worker

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -m jockey.worker health

CMD ["sh", "-c", "python -m jockey setup-kubeconfig && python -m jockey.worker start"]