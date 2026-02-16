# Yantra4D API — Production Docker Image
FROM python:3.12-slim

# OpenSCAD snapshot version — update hash after changing version:
#   wget -q <url> -O openscad && sha256sum openscad
ARG OPENSCAD_VERSION=2026.02.01
ARG OPENSCAD_SHA256=dad3a8d19e63c543129eabef314676ac9348ffcab727544f4283b2ae9000277c

# Install OpenSCAD snapshot (2026+) for Gridfinity extended syntax support
# AppImages require FUSE which isn't available in containers, so we extract
# the AppImage at build time and run the binary directly.
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  wget \
  fonts-liberation \
  fontconfig \
  libgl1 \
  libglu1-mesa \
  libharfbuzz0b \
  libegl1 \
  libwayland-client0 \
  libcomerr2 \
  libgpg-error0 \
  xvfb && \
  wget -q "https://files.openscad.org/snapshots/OpenSCAD-${OPENSCAD_VERSION}-x86_64.AppImage" \
  -O /tmp/openscad.AppImage && \
  echo "${OPENSCAD_SHA256}  /tmp/openscad.AppImage" | sha256sum -c - && \
  chmod +x /tmp/openscad.AppImage && \
  cd /opt && /tmp/openscad.AppImage --appimage-extract && \
  rm /tmp/openscad.AppImage && \
  ln -sf /opt/squashfs-root/AppRun /usr/local/bin/openscad && \
  rm -rf /var/lib/apt/lists/*

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

# Install project-bundled fonts into system fontconfig (belt-and-suspenders:
# the runtime FONTCONFIG_FILE env var also handles this, but having fonts
# system-installed in Docker is more robust).
RUN mkdir -p /usr/local/share/fonts/yantra4d && \
    find /app/projects -path '*/fonts/*.ttf' -exec cp {} /usr/local/share/fonts/yantra4d/ \; && \
    find /app/projects -path '*/fonts/*.otf' -exec cp {} /usr/local/share/fonts/yantra4d/ \; && \
    fc-cache -f /usr/local/share/fonts/yantra4d 2>/dev/null || true

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
# UID 1001 must match K8s deployment runAsUser
RUN useradd -r -u 1001 -s /bin/false yantra4d && chown -R yantra4d:yantra4d /app
USER yantra4d

CMD gunicorn -w 2 -b "0.0.0.0:${PORT}" --timeout 300 app:app
