# GPU Scheduler Check Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r gpucheck && useradd -r -g gpucheck gpucheck

# Copy application code
COPY main.py .
COPY requirements.txt .

# Install any dependencies (currently none)
RUN pip install --no-cache-dir -r requirements.txt

# Change ownership to non-root user
RUN chown -R gpucheck:gpucheck /app

# Switch to non-root user
USER gpucheck

# Set environment variables
ENV LOG_INTERVAL=10
ENV PYTHONUNBUFFERED=1

# Run the service
CMD ["python", "main.py"]