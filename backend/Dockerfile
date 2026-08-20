# Stage 1: Base image with Poetry installation
FROM python:3.12-slim AS base

WORKDIR /app

# Python and Poetry settings for Docker
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency configuration files
COPY pyproject.toml poetry.lock ./


# Stage 2: Development and testing environment
FROM base AS development

RUN poetry install

ENV PATH="/app/.venv/bin:$PATH"
COPY . .
CMD ["bash", "start.sh"]


# Stage 3: Intermediate production build stage
FROM base AS builder

RUN poetry install --only main


# Stage 4: Minimal production image
FROM python:3.12-slim AS production

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Copy isolated virtual environment (.venv) from builder stage
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY . .

CMD ["bash", "start.sh"]
