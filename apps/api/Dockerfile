# Qubic API — Production Docker Image
FROM python:3.12-slim

# Install OpenSCAD snapshot (2026+) for Gridfinity extended syntax support
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  wget \
  fonts-liberation \
  fontconfig \
  libgl1-mesa-glx \
  libglu1-mesa \
  xvfb && \
  wget -q https://files.openscad.org/snapshots/OpenSCAD-2026.02.01-x86_64.AppImage -O /usr/local/bin/openscad && \
  chmod +x /usr/local/bin/openscad && \
  rm -rf /var/lib/apt/lists/*

# Install custom fonts (Allerta Stencil for letter engravings)
COPY projects/tablaco/fonts/*.ttf /usr/share/fonts/truetype/custom/
RUN fc-cache -fv

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY apps/api/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application code
COPY projects/ ./projects/
COPY libs/ ./libs/
COPY apps/api/tests/ ./tests/
COPY apps/api/ ./backend/

# Environment configuration
ENV FLASK_DEBUG=false
ENV OPENSCAD_PATH=/usr/local/bin/openscad
ENV PORT=5000
ENV HOST=0.0.0.0
ENV PROJECTS_DIR=/app/projects
ENV OPENSCADPATH=/app/libs:/app/libs/dotSCAD/src
ENV VERIFY_SCRIPT=/app/tests/verify_design.py

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')" || exit 1

# Run with gunicorn for production
WORKDIR /app/backend

# Create non-root user
RUN useradd -r -s /bin/false qubic && chown -R qubic:qubic /app
USER qubic

CMD gunicorn -w 2 -b "0.0.0.0:${PORT}" --timeout 300 app:app
