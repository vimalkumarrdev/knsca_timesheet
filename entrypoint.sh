#!/bin/sh
set -e

echo "Waiting for database at $DB_HOST:$DB_PORT..."
until python -c "
import socket, os, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect((os.environ.get('DB_HOST', 'db'), int(os.environ.get('DB_PORT', 3306))))
    s.close()
except OSError:
    sys.exit(1)
"; do
  sleep 1
done
echo "Database is up."

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
