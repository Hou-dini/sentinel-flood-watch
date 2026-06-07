# ==============================================================================
# Sentinel Flood-Watch - Production Dockerfile
# Multi-stage build leveraging uv for dependency optimization
# ==============================================================================

# Stage 1: Dependency builder
FROM python:3.11-slim AS builder

# Install uv tool
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy configuration files first for caching
COPY backend/pyproject.toml backend/uv.lock ./backend/

# Sync dependencies without installing the project itself
RUN cd backend && uv sync --frozen --no-cache --no-install-project

# Stage 2: Final runtime environment
FROM python:3.11-slim

# Install curl and Node.js for running Node-based MCP servers
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @mongodb-js/mongodb-mcp-server && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment and packages from builder stage
COPY --from=builder /app/backend/.venv /app/backend/.venv

# Copy source code and frontend assets
COPY backend /app/backend
COPY frontend /app/frontend

# Create empty credentials and log directories
RUN mkdir -p /app/credentials

# Configure paths and runtime variables
ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONIOENCODING="utf-8"
ENV PYTHONPATH="/app/backend"

# Expose FastAPI server port
EXPOSE 8000

WORKDIR /app/backend

# Run Uvicorn server in production mode, dynamically binding to the Cloud Run PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
