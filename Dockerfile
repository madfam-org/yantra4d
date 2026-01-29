# Tablaco Backend - Production Docker Image
FROM python:3.12-slim

# Install system dependencies for OpenSCAD
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  openscad \
  fonts-liberation \
  fontconfig && \
  rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY web_interface/backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application code
COPY scad/ ./scad/
COPY tests/ ./tests/
COPY web_interface/backend/ ./backend/

# Environment configuration
ENV FLASK_DEBUG=false
ENV OPENSCAD_PATH=/usr/bin/openscad
ENV PORT=5000
ENV HOST=0.0.0.0
ENV SCAD_DIR=/app/scad
ENV VERIFY_SCRIPT=/app/tests/verify_design.py

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')" || exit 1

# Run with gunicorn for production
WORKDIR /app/backend

# Create non-root user
RUN useradd -r -s /bin/false tablaco && chown -R tablaco:tablaco /app
USER tablaco

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "300", "app:app"]
