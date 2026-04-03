FROM python:3.12-slim-bookworm

# Install system dependencies for cryptography (libssl) and zeroconf (avahi/mdns)
# Note: cryptography needs pre-built wheels — slim-bookworm provides libssl via apt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ src/

# Run as non-root for security
RUN useradd --system --no-create-home sonoff
USER sonoff

# Daemon entrypoint
CMD ["python", "-u", "src/__main__.py"]
