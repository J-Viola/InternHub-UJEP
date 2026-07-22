# InternHub - Systém pro správu praxí UJEP

## Přehled

InternHub je full-stack aplikace kombinující Django a React pro správu stáží a spolupráci mezi studenty a organizacemi na Univerzitě J. E. Purkyně v Ústí nad Labem.
Aplikace umožňuje organizacím spravovat nabídky stáží, studentům se přihlašovat a sledovat průběh stáží.
Zaměstnanci školy mohou spravovat a sledovat průběhy stáží studentů.
Aplikace je propojena se systémem STAG, který slouží k přihlašování zaměstnanců a studentů vysoké školy.

### Hlavní funkce

- **Správa uživatelů**: Studenti, firmy, akademičtí pracovníci
- **Správa nabídek praxí**: Vytváření, editace a schvalování nabídek
- **Přihlašování studentů**: Systém pro podávání přihlášek na praxe
- **Schvalovací procesy**: Workflow pro schvalování praxí a přihlášek
- **Dokumentace**: Správa a sdílení dokumentů
- **Integrace s ARES**: Automatické načítání dat o firmách
- **Integrace se STAG**: Synchronizace s univerzitním informačním systémem

## Technologický stack

### Backend
- **Django 5.2** - Python web framework
- **Django REST Framework** - API framework
- **PostgreSQL** - Databáze
- **Django Polymorphic** - Pro polymorfní modely uživatelů
- **JWT Authentication** - Autentizace

### Frontend
- **React 19.1** - JavaScript framework
- **React Router** - Navigace
- **Tailwind CSS** - Styling
- **Axios** - HTTP klient
- **React Icons** - Ikony

## Požadavky

- Docker 20.x nebo vyšší
- Docker Compose

## Instalace a spuštění

### 1. Klonování repozitáře
```bash
git clone <repository-url>
cd InternHub-UJEP
```

### 2. Konfigurace prostředí
Vytvořte soubor `.env` v kořenovém adresáři (viz [.env.example](.env.example)):
```env
# Database
PG_VERSION=15
PG_PASSWORD=your_password
PG_DB=internhub
PG_USER=internhub
PG_HOST=postgres
PG_PORT=5432

# Django
DJANGO_SECRET_KEY=your_secret_key
DEBUG=True

# Frontend
REACT_APP_API_URL=http://localhost:8000

# PgAdmin
PGADMIN_DEFAULT_EMAIL=admin@admin.com
PGADMIN_DEFAULT_PASSWORD=admin

# Python & Node versions
PY_VERSION=3.11
NODE_VERSION=18
```

### 3. Spuštění aplikace
```bash
docker compose up --build -d
```

Migrace databáze a nahrání počátečních dat proběhnou automaticky.
Spuštění migrací lze vypnout nastavením `MIGRATE_DEMO=0` v `.env`.

### 4. Přístup k aplikaci
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Dokumentace API (Swagger)**: http://localhost:8000/api/schema/swagger-ui
- **PgAdmin**: http://localhost:5050

## Testovací účty

Po migraci a naplnění databáze se můžete přihlásit pomocí následujících účtů:

### Organizace
| E-mail | Heslo |
|--------|-------|
| novak@jednatel.cz | demodemo |
| novak@inzerent.cz | demodemo |

### Admin
Je nutné se přihlásit pomocí způsobu "Jsem firma".
| E-mail | Heslo |
|--------|-------|
| admin@admin.com | demodemo |

### Zaměstnanci školy
Přihlášení probíhá na stránkách stag.demo.zcu.cz:
| Jméno | Login | Heslo |
|-------|-------|-------|
| Vedoucí katedry | indy | demo |
| Vedoucí předmětu | skalab | demo |

### Studenti
Přihlášení probíhá na stránkách stag.demo.zcu.cz:
| Jméno | Osobní číslo | Heslo |
|-------|-------------|-------|
| Martin Lacinová | D21B4304P | demo |
| Ondřej Kadlec | E22P9319P | demo |
| Daniil Marek | P20B4771P | demo |
| Matyáš Budina | S22P4307P | demo |
| Lucie Chadimová | Z21B4385P | demo |

## Databáze

V projektu je použita PostgreSQL databáze. Pro správu dat lze použít pgAdmin dostupný na adrese `http://localhost:5050`.

**Přihlašovací údaje pgAdmin:** admin@admin.com / admin

**Připojení k databázi:**
| Parametr | Hodnota |
|----------|---------|
| Host | internhub-postgres |
| Port | 5432 |
| Databáze | internhub |
| Uživatel | internhub |
| Heslo | internhub |

## Typy uživatelů

### Student
- Prohlížení nabídek praxí
- Podávání přihlášek
- Sledování stavu přihlášek
- Správa profilu

### Firma
- Vytváření nabídek praxí
- Správa firemního profilu
- Přehled přihlášených studentů
- Komunikace s univerzitou

### Akademický pracovník
- Schvalování nabídek praxí
- Správa studentů
- Koordinace praxí
- Přehledy a reporty

### Administrátor
- Správa uživatelů
- Systémová konfigurace
- Monitoring aplikace

## Struktura projektu

```
InternHub-UJEP/
├── backend/                 # Django backend
│   ├── api/                # Hlavní API aplikace
│   ├── department/         # Správa kateder
│   ├── practices/          # Správa praxí
│   ├── subject/            # Správa předmětů
│   ├── users/              # Správa uživatelů
│   └── app/                # Django konfigurace
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React komponenty
│   │   ├── pages/          # Stránky aplikace
│   │   ├── api/            # API klient
│   │   └── services/       # Služby
├── Tests/                  # Testovací dokumentace
├── docker-compose.yml      # Docker konfigurace
└── Makefile                # Automatizace úloh
```

## Dokumentace

Projekt obsahuje rozsáhlou dokumentaci v adresáři `Tests/`:
- **BDD testy** - Behavior Driven Development scénáře
- **UAT testy** - User Acceptance Testing
- **UML diagramy** - Architektura systému
- **Use Cases** - Případy použití
- **SRS dokumentace** - Software Requirements Specification

## Licence

Tento projekt je součástí bakalářské práce na Univerzitě J. E. Purkyně v Ústí nad Labem.
