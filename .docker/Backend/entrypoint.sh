#!/bin/sh
set -e

# 1. Spustit migrace (vytvoří tabulky, pokud neexistují)
echo "Spouštím migrace..."
python manage.py migrate

# 2. Pokud je zapnuto DEMO, resetujeme a naplníme DB
if [ "$MIGRATE_DEMO" = "1" ]; then
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