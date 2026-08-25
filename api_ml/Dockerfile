FROM python:3.12-slim

WORKDIR /app

COPY api_ml/requirements.txt /app/api_ml/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/api_ml/requirements.txt

COPY api_ml /app/api_ml
COPY models /app/models

EXPOSE 8000

CMD ["uvicorn", "api_ml.main:app", "--host", "0.0.0.0", "--port", "8000"]
