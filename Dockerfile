# Multi-stage Docker build for taskd
# Stage 1: Build React frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ .

# Build the React app (outputs to /app/dist by default)
RUN npm run build

# Stage 2: Python backend with static files
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r taskd && useradd -r -g taskd taskd

WORKDIR /app

# Install system dependencies for SQLite and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend files
COPY backend/ .

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy static files from frontend builder
# Vite builds to /app/dist by default
COPY --from=frontend-builder /app/dist /app/static

# Create data directory and set permissions
RUN mkdir -p /data && chown taskd:taskd /data

# Switch to non-root user
USER taskd

# Expose port
EXPOSE 8000

# Set environment variables
ENV PORT=8000
ENV DATA_DIR=/data

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
