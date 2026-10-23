FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal OS dependencies for Postgres client library & healthcheck curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged application user
RUN groupadd -g 10001 meshapp && \
    useradd -u 10001 -g meshapp -s /bin/bash -m meshapp

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and adjust ownership
COPY . .
RUN chown -R meshapp:meshapp /app

# Switch to unprivileged runtime user
USER meshapp

# Expose FastAPI application port
EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production server execution
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
