#!/bin/sh
# Container start: apply migrations, optionally seed sample directory data, start the API.
set -e

echo "Applying database migrations..."
alembic upgrade head

if [ "${SEED_SAMPLE_DATA:-false}" = "true" ]; then
  python scripts/import_data.py all data/sample_directory.json --if-empty
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
