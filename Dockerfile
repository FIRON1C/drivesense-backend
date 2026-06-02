# Use a slim Python image for a smaller footprint
FROM python:3.11-slim

# Install system-level PostgreSQL libraries
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code
COPY . .

# Expose port and run Gunicorn
EXPOSE 8080
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} main:app"]
