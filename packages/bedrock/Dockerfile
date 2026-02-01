# This should be run from project root e.g., $ docker build -f packages/bedrock/Dockerfile <project_root>
# Stage 1: Builder - Install dependencies with full workspace access
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim as builder

WORKDIR /build

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_PROGRESS=1

# Copy important parts of workspace so uv can resolve workspace dependencies
COPY packages packages
COPY pyproject.toml pyproject.toml

# Install all packages
RUN uv pip install \
  --target /install \
  /build/packages/shared \
  /build/packages/bedrock

# Stage 2: Runtime - Minimal image with only what's needed
FROM python:3.14-bookworm-slim

WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /install /usr/local/lib/python3.14/site-packages

# Copy bedrock source code
COPY packages/bedrock/src /app/src

# Environment variables
ENV PYTHONUNBUFFERED=1 \
  DOCKER_CONTAINER=1 \
  PATH="/usr/local/bin:$PATH"

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 9000 8000 8080

# Run the application
CMD ["opentelemetry-instrument", "python", "-m", "sb_bedrock.main"]
