FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Create necessary directories with open permissions (HF Spaces runs as non-root)
RUN mkdir -p uploads chroma_db mlruns && chmod -R 777 uploads chroma_db mlruns

# HF Spaces default port
EXPOSE 7860

# Healthcheck so HF Spaces knows the app is up
HEALTHCHECK --interval=30s --timeout=10s CMD curl -f http://localhost:7860/ || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
