#!/bin/sh
# Startup script that safely handles both fresh and imported databases

# Check if django_content_type table exists
TABLE_EXISTS=$(sqlite3 db.sqlite3 "SELECT name FROM sqlite_master WHERE type='table' AND name='django_content_type';" 2>/dev/null)

if [ -n "$TABLE_EXISTS" ]; then
    echo "Database already has Django tables - using --fake to skip migrations"
    # Database already has Django tables, just mark migrations as applied
    python manage.py migrate --fake --verbosity=0
else
    echo "Fresh database - running migrations normally"
    # Fresh database, run migrations to create tables
    python manage.py migrate --fake-initial --verbosity=0
fi

# Start Django development server
exec python manage.py runserver 0.0.0.0:${BACKEND_PORT:-8000}
