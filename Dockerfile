FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    curl \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY frontend/package.json /app/frontend/package.json
RUN cd /app/frontend && npm install

COPY . /app

RUN mkdir -p /app/data/books /app/data/audio /app/data/reference

ENV PYTHONPATH=/app/backend
ENV NODE_ENV=production

EXPOSE 8000 5173

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
