FROM python:3.11-slim

WORKDIR /app

# System dependencies for asyncpg, PyMuPDF, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY start.sh .
RUN chmod +x start.sh

# Local uploads directory (dev only, not used when GCS is configured)
RUN mkdir -p uploads

ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
