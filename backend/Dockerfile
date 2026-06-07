FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and set timeout/retry
RUN pip install --upgrade pip

# Install light dependencies first (cached layer)
COPY requirements-light.txt .
RUN pip install --no-cache-dir --default-timeout=100 --retries=5 -r requirements-light.txt

# Install heavy dependencies separately
COPY requirements-heavy.txt .
RUN pip install --no-cache-dir --default-timeout=100 --retries=5 -r requirements-heavy.txt

# Copy application code
COPY . .
COPY demo_trajectories /app/demo_trajectories
COPY high_conf_bots.json /app/high_conf_bots.json
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]