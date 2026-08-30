FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[dev]"

COPY . .

# --timeout 120 because three sequential Gemini calls on a cold free-tier
# connection can exceed gunicorn's 30s default and be killed mid-answer.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--timeout", "120"]
