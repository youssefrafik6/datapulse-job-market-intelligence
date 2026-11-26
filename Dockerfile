FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install '.[dev]'
COPY . .
RUN useradd --create-home datapulse && mkdir -p data/raw data/processed results && chown -R datapulse:datapulse /app
USER datapulse
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
