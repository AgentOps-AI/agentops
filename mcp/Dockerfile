FROM python:3.12-slim

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY server.py ./

# Create and activate virtual environment, then install dependencies
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HOST=https://api.agentops.ai

# Run the MCP server using the virtual environment
CMD [".venv/bin/python", "server.py"]