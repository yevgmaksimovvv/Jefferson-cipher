FROM python:3.10.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY tests ./tests

RUN pip install --no-cache-dir -e ".[dev]"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
