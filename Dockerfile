# ── Stage 1: Build ───────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Install the package itself
RUN pip install --no-cache-dir -e .

# ── Stage 2: Runtime ─────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages and app from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Create data directory for reflection persistence
RUN mkdir -p /app/data

# Expose the API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default: run the FastAPI server
CMD ["uvicorn", "app.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
