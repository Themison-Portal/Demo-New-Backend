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
COPY alembic/ alembic/
COPY alembic.ini .
COPY start.sh .
RUN chmod +x start.sh

# Local uploads directory (dev only, not used when GCS is configured)
RUN mkdir -p uploads

ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

# Run pending alembic migrations, then start the app.
# - `alembic upgrade head` is a no-op when the DB is already current.
# - The `&&` short-circuit means the container exits non-zero if migrations
#   fail, so we never serve traffic against an out-of-sync schema.
# - `exec` replaces the shell with uvicorn so SIGTERM from the orchestrator
#   reaches uvicorn directly (graceful shutdown).
CMD alembic -c alembic.ini upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
