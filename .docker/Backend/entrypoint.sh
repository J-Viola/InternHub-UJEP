#!/bin/sh
set -e

# A-20: jednotné parsování boolean proměnných (1/true/yes/on, bez ohledu na velikost písmen)
env_bool() {
    case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')" in
        1|true|yes|on) return 0 ;;
        *) return 1 ;;
    esac
}

# 0. A-13: demo reset (flush) je povolen jen ve vývojovém režimu — fail-closed
if env_bool "$MIGRATE_DEMO" && ! env_bool "$DEBUG"; then
    echo "CHYBA: MIGRATE_DEMO=1 je povoleno jen při DEBUG=True (demo reset provádí flush databáze)." >&2
    exit 1
fi

# 1. Spustit migrace (vytvoří tabulky, pokud neexistují)
echo "Spouštím migrace..."
python manage.py migrate

# 2. Pokud je zapnuto DEMO, resetujeme a naplníme DB
if env_bool "$MIGRATE_DEMO"; then
    echo "--- REŽIM DEMO AKTIVNÍ ---"
    
    # A. Vyčištění databáze (smaže všechna data, ale nechá tabulky)
    echo "1. Mazání starých dat (flush)..."
    python manage.py flush --no-input
    
    # B. Základní číselníky a Admin (nutné pro fake data)
    echo "2. Vytváření základních dat (Role, Admin, Katedry)..."
    python manage.py seed_db
    
    # C. Generování náhodných dat
    echo "3. Generování fake dat (Studenti, Firmy, Praxe)..."
    python manage.py seed_fake
    
    echo "--- SEEDOVÁNÍ DOKONČENO ---"
fi

# 3. Spustit hlavní příkaz (runserver)
exec "$@"
