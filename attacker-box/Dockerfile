# Minimal, non-root sandbox for the in-browser terminal's allowlisted tools.
# Deliberately NOT given any host mount, Docker socket, or secret material.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        dnsutils \
        nmap \
        iputils-ping \
        whois \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 voidlab
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY exec_server.py .

USER voidlab
EXPOSE 7000

CMD ["gunicorn", "--bind", "0.0.0.0:7000", "--workers", "2", "--timeout", "30", "exec_server:app"]
