FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/output \
    && chown -R appuser:appuser /app

USER appuser

ENV OUTPUT_DIR=/app/output \
    PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
