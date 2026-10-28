FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0 \
    && useradd --create-home --uid 1000 esoteric

COPY . .
USER esoteric

EXPOSE 5000

# One worker: the HQ9+ accumulator is kept in process memory.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "esoteric_chat.server:create_app()"]
