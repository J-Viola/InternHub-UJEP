#!/bin/bash
set -e

# Spustíme postgres ENTRYPOINT na pozadí
exec docker-entrypoint.sh postgres "$@" &

if [ "$MIGRATE_DEMO" = 1 ]; then


  until pg_isready -U "$PG_USER"; do
    echo "Waiting for postgres..."
    sleep 2
  done
  echo "Disconnecting all users from $POSTGRES_DB..."
  PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();"

  PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";"
  PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\";"
  echo "Importing init.sql..."
  PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /app/database/init.sql
  echo "Import completed."
else
  echo "MIGRATE is not enabled. Skipping import."
fi
wait