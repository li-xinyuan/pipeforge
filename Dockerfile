# === Build Stage: Frontend ===
FROM node:20-alpine AS build-frontend

WORKDIR /app/configforge-web
COPY configforge-web/package.json configforge-web/package-lock.json ./
# NOTE: 不在此处设 NODE_ENV=production —— npm ci 会跳过 devDependencies，
# 而 build 脚本依赖 vue-tsc / vite（均在 devDependencies）。
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

ENV CONFIGFORGE_ENV=production

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Start server
CMD ["uvicorn", "configforge.server:app", "--host", "0.0.0.0", "--port", "8000"]
