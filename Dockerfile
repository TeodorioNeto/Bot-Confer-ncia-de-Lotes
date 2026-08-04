FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=container \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    TZ=America/Manaus

WORKDIR /app

COPY requirements.txt .

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install-deps chromium \
    && python -m playwright install chromium

COPY *.py ./
COPY doc.html logo-lg.png ./
COPY web/ ./web/
COPY src/ ./src/

CMD ["python", "main.py"]
