# To run this Dockerfile, do so from the repository root directory
# docker build -f api/Dockerfile -t agentops-api .

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY api/pyproject.toml /app/

COPY api/agentops /app/agentops
COPY deploy/jockey /app/jockey

RUN uv sync

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "agentops.app:app", "--host", "0.0.0.0", "--port", "8000"]
