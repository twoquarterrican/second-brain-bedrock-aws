# This should be run from project root e.g., $ docker build -f packages/bedrock/Dockerfile <project_root>
# Stage 1: Builder - Install dependencies with full workspace access
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /build

COPY pyproject.toml pyproject.toml
COPY packages packages

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_PROGRESS=1

# Install all packages (without --target so executables go to proper location)
RUN uv pip install \
  /build/packages/shared \
  /build/packages/bedrock \
  aws-opentelemetry-distro==0.12.2

# Stage 2: Runtime - Minimal image with only what's needed
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

# Copy site-packages from builder
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages

# Copy executables (scripts like opentelemetry-instrument)
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy bedrock source code
COPY packages/bedrock/src /app/src

# Environment variables
ENV PYTHONUNBUFFERED=1 \
  DOCKER_CONTAINER=1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 9000 8000 8080

#CMD ["opentelemetry-instrument", "python", "-m", "sb_bedrock.main"]
CMD ["python", "-m", "sb_bedrock.main"]
