#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] waiting for postgres at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
until python - <<'PY'
import os, socket, sys
host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1)
try:
    s.connect((host, port))
except OSError:
    sys.exit(1)
sys.exit(0)
PY
do
  sleep 1
done
echo "[entrypoint] postgres is reachable."

echo "[entrypoint] generating migrations for VOIDLAB apps..."
python manage.py makemigrations accounts labs --noinput

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${DJANGO_SEED_DATA:-true}" = "true" ]; then
  echo "[entrypoint] seeding OWASP Top 10:2025 categories + lab catalog..."
  python manage.py seed_labs
fi

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  echo "[entrypoint] ensuring superuser '${DJANGO_SUPERUSER_USERNAME}' exists..."
  python manage.py createsuperuser --noinput \
    --username "${DJANGO_SUPERUSER_USERNAME}" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@voidlab.local}" || true
fi

exec "$@"
