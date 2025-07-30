# InternHub

## Přehled
InternHub je full-stack aplikace kombinující Django a React pro správu stáží a spolupráce mezi studenty a organizacemi.
Aplikace umožňuje organizacím spravovat nabídky stáží, studentům umožnuje se přihlašovat a sledovat průběh stáží. 
Zaměstnanci školy mohou spravovat a sledovat průběhy stáží studentů.
Aplikace je propojena s aplikaci STAG, která slouží k přihlašování zaměstnanců/studentů vysoké školy.

## Požadavky
- Docker 20.x nebo vyšší
- Docker Compose

## Instalace a spuštění
1. Naklonujte repozitář
2. V kořenovém adresáři projektu spusťte:
   ```bash
   docker-compose up --build -d
   ```
3. Služby se spustí, migrace proběhnou automaticky a počáteční data budou nahrána. Dá se vypnout za pomocí nastavení v env: **MIGRATE_DEMO=0**

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

## Dokumentace API
Dostupná na http://localhost:8000/api/schema/swagger-ui


## Technické detaily
- Backend: Django, Django REST Framework
- Frontend: React
- Databáze: PostgreSQL
- Frontend běží na portu 3000, backend na portu 8000
- Proměnné prostředí nakonfigurovány v `docker-compose.yml` a `.env`
