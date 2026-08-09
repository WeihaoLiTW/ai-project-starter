#!/bin/sh
# Migrations run here, not in GitHub Actions: Actions cannot reach the SQLite
# file, which lives on a volume inside this container.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Two workers. SQLite serialises writes, so more workers buy contention, not
# throughput.
exec gunicorn project.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --access-logfile -
