#!/bin/bash

echo "Applying Alembic migrations (creating tables)..."
alembic upgrade head

echo "Seeding PostgreSQL with initial rules..."
python -m app.scripts.seed_db

echo "Starting FastAPI application..."
exec uvicorn main:app --host 0.0.0.0 --port 8080 --reload
