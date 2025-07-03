FROM python:3.11-slim

# Install system dependencies for building and frontend assets
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential nodejs npm && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Build frontend assets
COPY package.json ./package.json
COPY scripts ./scripts
RUN npm install && npm run build

COPY . .

EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
