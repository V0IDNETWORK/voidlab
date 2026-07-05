FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        iputils-ping \
    && rm -rf /var/lib/apt/lists/*

ARG LAB_FLAG="VOIDLAB{c0mm4nd_1nj3ct10n_v14_sh3ll_m3t4ch4rs}"
RUN echo "${LAB_FLAG}" > /flag.txt && chmod 644 /flag.txt

RUN useradd --create-home --uid 10012 lab
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER lab
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
