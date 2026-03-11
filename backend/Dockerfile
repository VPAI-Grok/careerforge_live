# ── CareerForge Backend — Cloud Run Dockerfile ────────────────────────────────
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr (important for Cloud Run logs)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies (needed by reportlab for PDF generation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run sets the PORT env var; default to 8080
ENV PORT=8080

# Run the FastAPI server with uvicorn
# - host 0.0.0.0 is required for Cloud Run
# - workers=1 is recommended for WebSocket support
CMD exec uvicorn career_counselor_agent.api.server:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers 1 \
    --timeout-keep-alive 300
