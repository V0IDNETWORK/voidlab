FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10002 voidlab
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/staticfiles /app/media && chown -R voidlab:voidlab /app
RUN chmod +x /app/entrypoint.sh

USER voidlab

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
# Daphne serves both plain HTTP and the /ws/ WebSocket upgrade from one ASGI app.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
