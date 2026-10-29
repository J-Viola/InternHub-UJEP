#!/bin/sh
set -e

# A-23: produkční entrypoint — žádný flush, seed_db ani seed_fake (viz A-13).
# Migrace a collectstatic běží jen u webové služby (příkaz obsahuje gunicorn); celery worker a scheduler je nespouštějí.
case "$*" in
    *gunicorn*)
        echo "Spouštím migrace..."
        python manage.py migrate --noinput
        echo "Sbírám statické soubory..."
        python manage.py collectstatic --noinput
        ;;
esac

exec "$@"
