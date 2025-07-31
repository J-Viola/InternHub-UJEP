# InternHub - Systém pro správu praxí UJEP

## Popis projektu

InternHub je moderní webová aplikace pro správu a koordinaci studentských praxí na Univerzitě J. E. Purkyně v Ústí nad Labem. Systém umožňuje efektivní komunikaci mezi studenty, firmami a akademickými pracovníky v rámci procesu organizace a realizace praxí.

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

##  Instalace a spuštění

### Předpoklady
- Docker a Docker Compose
- Make (volitelně)

### 1. Klonování repozitáře
```bash
git clone <repository-url>
cd InternHub-UJEP
```

### 2. Konfigurace prostředí
Vytvořte soubor `.env` v kořenovém adresáři:
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
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin_password

# Python & Node versions
PY_VERSION=3.11
NODE_VERSION=18
```

### 3. Spuštění aplikacese
```bash
docker compose up --build -d
```

### 4. Přístup k aplikaci
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **PgAdmin**: http://localhost:5050

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
├── docker-compose.yaml     # Docker konfigurace
└── Makefile               # Automatizace úloh
```

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

## Dokumentace

Projekt obsahuje rozsáhlou dokumentaci v adresáři `Tests/`:
- **BDD testy** - Behavior Driven Development scénáře
- **UAT testy** - User Acceptance Testing
- **UML diagramy** - Architektura systému
- **Use Cases** - Případy použití
- **SRS dokumentace** - Software Requirements Specification


## Licence

Tento projekt je součástí bakalářské práce na Univerzitě J. E. Purkyně v Ústí nad Labem.

