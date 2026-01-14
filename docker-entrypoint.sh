#!/bin/bash
set -e

echo "Running database migrations..."
python manage.py migrate --noinput

# Create superuser if password is set
if [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser..."
    python manage.py create_superuser || true
fi

echo "Starting gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --threads 4 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --log-level info
