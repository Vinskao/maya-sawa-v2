FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl libpq5 libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy only pyproject to leverage Docker layer cache
COPY pyproject.toml /app/

# Generate lock file if missing and install dependencies
RUN poetry lock && poetry install --no-root --with prod --without dev

# Copy project
COPY . /app

EXPOSE 8000

# Default env (override in k8s)
ENV DJANGO_SETTINGS_MODULE=config.settings.production \
    PORT=8000 \
    GUNICORN_CMD_ARGS="--workers=1 --threads=4 --bind=0.0.0.0:8000 --timeout 120"

# Entrypoint script (migrations/static handled by initContainers on k8s)
CMD ["bash", "-lc", "gunicorn config.wsgi:application"]



