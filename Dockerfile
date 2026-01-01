# Multi-stage build for NBA Over/Under app
FROM node:20-slim AS frontend-builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY . .

# Build frontend (CACHE BUST: 2025-12-29-11:00-DECISION-CARD)
RUN npm run build

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies REQUIRED for scipy compilation
# scipy is a MANDATORY dependency for archetype percentile calculations
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies - scipy is REQUIRED (app will crash without it)
# Build tools installed above are necessary for scipy wheel compilation
RUN pip install --no-cache-dir -r requirements.txt && \
    echo "=== Python Dependencies Installed ===" && \
    pip show scipy && \
    echo "✓ scipy successfully installed" || (echo "✗ CRITICAL: scipy installation failed" && exit 1)

# Copy application code
COPY . .

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/dist ./dist

# Expose port (Railway will set PORT env var)
EXPOSE 8080

# Start the application
CMD gunicorn server:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
