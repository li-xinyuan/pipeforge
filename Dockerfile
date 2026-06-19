# === Build Stage: Frontend ===
FROM node:20-alpine AS build-frontend

ENV NODE_ENV=production

WORKDIR /app/configforge-web
COPY configforge-web/package.json configforge-web/package-lock.json ./
RUN npm ci
COPY configforge-web/ ./
RUN npm run build

# === Runtime Stage: Backend ===
FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

# Copy backend code
COPY configforge/ ./configforge/
COPY src/ ./src/

# Copy built frontend assets
COPY --from=build-frontend /app/configforge-web/dist ./configforge/static/

# Create data and temp directories
RUN mkdir -p data tmp/uploads tmp/logs

# Create non-root user and set ownership
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Start server
CMD ["uvicorn", "configforge.server:app", "--host", "0.0.0.0", "--port", "8000"]
