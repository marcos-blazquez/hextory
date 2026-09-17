# Hextory on-prem API (DES-0004)
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY adapters ./adapters
COPY config ./config
COPY docs ./docs

RUN pip install --no-cache-dir -e ".[onprem]"

ENV HEXTORY_ONPREM_HOST=0.0.0.0
ENV HEXTORY_ONPREM_PORT=8080

EXPOSE 8080

CMD ["python", "-m", "adapters.onprem"]
