#!/usr/bin/env bash
# A-14: lokální smoke test produkčního stacku (docker-compose.prod.yaml) vedle vývojového.
# Běží pod projektem `internhub-prod-smoke`, s vlastními jmény kontejnerů, sítí a svazky
# (vývojový stack ani jeho svazky se nedotýká). Na konci se smaže JEN tento projekt (down -v).
#
# Použití: scripts/verify_prod_stack.sh            (výchozí port 18080; přepsat SMOKE_PORT=...)
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT=internhub-prod-smoke
PORT="${SMOKE_PORT:-18080}"
TMP="$(mktemp -d)"
FAILS=0
H='X-Forwarded-Proto: https'
SMOKE_HOST=internhub.smoke.test
PW='Sm0ke-Pass-123!'

compose() {
    docker compose -p "$PROJECT" --env-file "$TMP/env" -f docker-compose.prod.yaml -f "$TMP/override.yaml" "$@"
}
cleanup() {
    compose down -v --remove-orphans >/dev/null 2>&1 || true
    rm -rf "$TMP"
}
trap cleanup EXIT

check() { # popis, očekávaný kód, skutečný kód
    if [ "$2" = "$3" ]; then echo "OK   $1 ($3)"; else echo "FAIL $1 (očekáváno $2, je $3)"; FAILS=$((FAILS + 1)); fi
}
# Host header = jediná povolená doména (ALLOWED_HOSTS bez localhostu, jako v produkci)
code() { curl -s -o /dev/null -w '%{http_code}' -H "Host: $SMOKE_HOST" "$@"; }

cat > "$TMP/env" <<EOF
PY_VERSION=3.13
NODE_VERSION=18
PG_DB=internhub
PG_USER=internhub
PG_PASSWORD=smokepass
PG_HOST=postgres
PG_PORT=5432
DEBUG=False
DEMO_LOGIN=0
MIGRATE_DEMO=0
STAG_MOCK=False
STAG_WS_URL=https://stag-demo.zcu.cz/ws
DJANGO_SECRET_KEY=smoke-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz
JWT_SECRET_KEY=smoke-jwt-secret-0123456789-abcdefghijklmnop
JWT_ACCESS_TOKEN_REFRESH_TIME=300
# Platný Fernet klíč (32 nulových bajtů) — produkce ho vyžaduje.
STAG_TICKET_ENCRYPTION_KEY=MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=
ALLOWED_HOSTS=$SMOKE_HOST
FRONTEND_URL=http://localhost:$PORT
REDIS_URL=redis://redis:6379/0
CORS_ALLOWED_ORIGINS=http://localhost:$PORT
EMAIL_HOST=localhost
EOF
cat > "$TMP/override.yaml" <<EOF
services:
  postgres: { container_name: smoke-postgres }
  redis: { container_name: smoke-redis }
  django:
    container_name: smoke-backend
    env_file: !override [$TMP/env]
  celery-worker:
    container_name: smoke-celery-worker
    env_file: !override [$TMP/env]
  scheduler:
    container_name: smoke-scheduler
    env_file: !override [$TMP/env]
  frontend:
    container_name: smoke-frontend
    ports: !override ["$PORT:80"]
networks:
  internhub:
    name: internhub-prod-smoke
EOF

echo "== A-13: entrypoint odmítne MIGRATE_DEMO=1 bez DEBUG=True (bez databáze)"
set +e
MIGRATE_DEMO=1 DEBUG=False sh .docker/Backend/entrypoint.sh true >/dev/null 2>&1
check "MIGRATE_DEMO=1 DEBUG=False → exit 1" 1 $?
set -e

echo "== A-02/A-23: build a start prod stacku"
compose up -d --build --wait --wait-timeout 300 postgres redis django celery-worker scheduler frontend >/dev/null

for c in smoke-backend smoke-celery-worker smoke-scheduler; do
    check "$c běží jako appuser" appuser "$(docker exec "$c" id -un)"
    check "$c bez restartů" 0 "$(docker inspect -f '{{.RestartCount}}' "$c")"
done

echo "== A-27: scheduler (supercronic) načetl crontab a příkazy z něj doběhnou"
sleep 2
if docker logs smoke-scheduler 2>&1 | grep -q "read crontab"; then check "scheduler načetl crontab" 0 0; else check "scheduler načetl crontab" 0 1; fi
if docker exec smoke-celery-worker sh -c "celery -A app inspect registered 2>/dev/null | grep -q export_data_async" ; then check "worker má úlohu exportu" 0 0; else check "worker má úlohu exportu" 0 1; fi
docker exec smoke-scheduler sh -c "grep -vE '^[[:space:]]*(#|$)' /app/backend/crontab | cut -d' ' -f6-" > "$TMP/cron_cmds"
while IFS= read -r cmd; do
    docker exec smoke-scheduler sh -c "$cmd" >/dev/null 2>&1
    check "cron příkaz: $cmd" 0 $?
done < "$TMP/cron_cmds"

echo "== A-22: X-Forwarded-Proto"
BASE="http://localhost:$PORT"
check "/api/health/ bez hlavičky → 301" 301 "$(code "$BASE/api/health/")"
check "/api/health/ s X-Forwarded-Proto: https → 200" 200 "$(code -H "$H" "$BASE/api/health/")"

echo "== A-23: statika admina"
check "admin CSS" 200 "$(code -H "$H" "$BASE/static/django/admin/css/base.css")"
check "/admin/login/" 200 "$(code -H "$H" "$BASE/admin/login/")"

echo "== A-22/A-01: /storage (200 / 404 (A-20) / nikdy 500)"
docker exec smoke-backend sh -c "mkdir -p storage/images/logos storage/documents && echo x > storage/images/logos/t.png && echo x > storage/documents/t.docx"
docker exec smoke-backend python manage.py shell -c "
from users.models import OrganizationUser, StudentUser
OrganizationUser.objects.create_superuser(email='adm@smoke.local', password='$PW')
s = StudentUser.objects.create(email='stu@smoke.local', os_cislo='S1', is_active=True); s.set_password('$PW'); s.save()
" >/dev/null
tok() {
    curl -s -H "Host: $SMOKE_HOST" -H "$H" -H 'Content-Type: application/json' -d "{\"email\":\"$1\",\"password\":\"$PW\"}" "$BASE/api/users/login/" |
        python3 -c "import sys,json;print(json.load(sys.stdin).get('access',''))"
}
TA="$(tok adm@smoke.local)"; TS="$(tok stu@smoke.local)"
check "logo (veřejné)" 200 "$(code -H "$H" "$BASE/storage/images/logos/t.png")"
check "dokument bez tokenu" 401 "$(code -H "$H" "$BASE/storage/documents/t.docx")"
check "dokument admin" 200 "$(code -H "$H" -H "Authorization: Bearer $TA" "$BASE/storage/documents/t.docx")"
check "dokument cizí student" 404 "$(code -H "$H" -H "Authorization: Bearer $TS" "$BASE/storage/documents/t.docx")"

echo "== A-13/A-23: prod image nespouští flush ani seed"
if docker exec smoke-backend sh -c "grep -v '^[[:space:]]*#' /entrypoint.prod.sh | grep -qE 'flush|seed_db|seed_fake'"; then check "entrypoint.prod.sh bez flush/seed" 0 1; else check "entrypoint.prod.sh bez flush/seed" 0 0; fi

echo
if [ "$FAILS" -eq 0 ]; then echo "SMOKE OK"; else echo "SMOKE SELHAL ($FAILS chyb)"; exit 1; fi
