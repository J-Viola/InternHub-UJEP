# InternHub

## Přehled
InternHub je full-stack aplikace kombinující Django a React pro správu stáží a uživatelských účtů.

## Požadavky
- Docker 20.x nebo vyšší
- Docker Compose

## Instalace a spuštění
1. Naklonujte repozitář
2. V kořenovém adresáři projektu spusťte:
   ```bash
   docker-compose up --build
   ```
3. Služby se spustí, migrace proběhnou automaticky a počáteční data budou nahrána.

## Testovací účty
Po migraci a naplnění databáze se můžete přihlásit pomocí následujících účtů:

### Organizace
- novak@jednatel.cz / demodemo
- novak@inzerent.cz / demodemo

### Stag uživatelé
Přihlášení bude probíhat na stránkách stag.demo.zcu.cz, kde jsou dostupné následující účty:
- Vedoucí katedry: indy / demo
- Student: Z21B4385P / demo
- Vedoucí předmětu: skalab / demo


## Databáze
V projektu je použita PostgreSQL databáze. K ní se dá použít pgAdmin pro správu dat. 
Přihlašovací údaje jsou následující: admin@admin.com / admin a nachází se na adrese `http://localhost:5050`.

#### Pro přístup k databázi použijte následující přihlašovací údaje:
- HOST: internhub-postgres
- PORT: 5432
- DB: internhub
- Uživatel: internhub
- Heslo: internhub


## Technické detaily
- Backend: Django 4.x, Django REST Framework
- Frontend: React 18, Create React App
- Databáze: PostgreSQL
- Dokumentace API dostupná na `/api/schema/` a procházení na `/api/`
- Frontend běží na portu 3000, backend na portu 8000
- OAuth2 autentizace s JWT tokeny
- Proměnné prostředí nakonfigurovány v `docker-compose.yml` a `.env`
