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

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements (CACHE BUST: 2025-12-31-scipy-install)
COPY requirements.txt .

# Install Python dependencies including scipy
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/dist ./dist

# Expose port (Railway will set PORT env var)
EXPOSE 8080

# Start the application
CMD gunicorn server:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
