FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY app/database/migrations ./app/database/migrations

RUN pip install --no-cache-dir .

EXPOSE 8000

# Listen on 0.0.0.0 *inside the container* so the frontend service can reach it
# over the compose network; host/LAN exposure is controlled by docker-compose
# publish bindings (see docker-compose.yml + docs/SECURITY_NOTES.md, Q1).
# Migrations run on startup inside create_app; universe seeding is idempotent.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
