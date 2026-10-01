# Stage 1: Base Python 3.11 Slim Image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace

WORKDIR /workspace

# Install system dependencies needed for compiling psycopg2 and C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest
COPY requirements.txt /workspace/requirements.txt

# Install locked Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source tree and models
COPY backend /workspace/backend
COPY ml /workspace/ml
COPY monitoring /workspace/monitoring

# Create dedicated non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /workspace

USER appuser

# Expose FastAPI port
EXPOSE 8000

# Health check to ensure Uvicorn is serving requests
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start Uvicorn server
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]