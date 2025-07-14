# Multi-stage build for GPU scheduler
FROM python:3.9-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.9-slim

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash scheduler

# Set working directory
WORKDIR /app

# Copy installed packages from builder and fix permissions
COPY --from=builder --chown=scheduler:scheduler /root/.local /home/scheduler/.local

# Copy application code
COPY --chown=scheduler:scheduler scheduler.py .
COPY --chown=scheduler:scheduler health_server.py .
COPY --chown=scheduler:scheduler webhook_server.py .

# Create directories for certificates
RUN mkdir -p /certs && chown scheduler:scheduler /certs

# Set Python path to include user packages
ENV PATH=/home/scheduler/.local/bin:$PATH
ENV PYTHONPATH=/home/scheduler/.local/lib/python3.9/site-packages

# Switch to non-root user
USER scheduler

# Default to running the scheduler (can be overridden)
CMD ["python", "-u", "scheduler.py"]