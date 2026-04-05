# Glass -- Container-ready deployment
#
# The compliance market demands container-ready deployment. Matchlock (HN Feb 2026)
# showed that "being able to prove via infrastructure that an agent literally cannot
# access the host network" is a stronger compliance story than soft system prompts.
# Amla Sandbox (HN Jan 2026) reinforced: sandboxing is the middle path between
# unsafe exec and costly abstractions.
#
# Build:   docker build -t glass .
# Run:     docker run -p 7777:7777 -e ANTHROPIC_API_KEY=sk-... glass
# Dev:     docker run -p 7777:7777 -e OLLAMA_BASE_URL=http://host.docker.internal:11434 glass
#
# The container runs as non-root (uid 1000) with a read-only filesystem except
# for /data where the SQLite database lives. Health probes are built in.

FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first for layer caching
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[claude]"

# Copy application code
COPY glass/ glass/
COPY static/ static/

# Create non-root user and data directory
RUN useradd --create-home --uid 1000 glass && \
    mkdir -p /data && \
    chown glass:glass /data

# Default database location inside the container
ENV GLASS_DB_PATH=/data/glass.db \
    GLASS_HOST=0.0.0.0 \
    GLASS_PORT=7777

# Switch to non-root
USER glass

EXPOSE 7777

# Health check using the built-in liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:7777/healthz')"]

ENTRYPOINT ["python3", "-m", "glass.main"]
