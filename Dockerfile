FROM python:3.13-slim

WORKDIR /app

ENV PYTHONPATH=/app

# Install dependencies first (cached layer)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

EXPOSE 8000

CMD ["python", "run.py"]
