FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and browsers
RUN pip install playwright && \
    playwright install --with-deps chromium

# Copy application files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create data directories
RUN mkdir -p ~/.mcp-browser/{profiles,cookies,logs}

# Expose port
EXPOSE 9377

# Default: run HTTP server
CMD ["python3", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "9377"]

# Alternative: run MCP stdio server
# CMD ["python3", "mcp_server.py"]