# Přehled Testování v Aplikaci InternHub

Tento dokument poskytuje přehled automatizovaných testů, které pokrývají klíčové součásti backendu i frontendu.

---

### **1. Backend (Django REST Framework)**
Celkem **82 testů**, které se zaměřují na integritu dat, byznys logiku a oprávnění.

#### **Správa uživatelů a Auth (`users`)**
*   **Autentizace:**
    *   Přihlášení přes e-mail a heslo (JWT).
    *   Ověření STAG ticketu pro přihlášení studentů a učitelů.
    *   Automatické vytvoření/načtení STAG uživatele při prvním přihlášení.
*   **Registrace:**
    *   Registrace nového firemního uživatele.
    *   Ověření unikátnosti e-mailu.
    *   Integrace s ARES API pro automatické doplnění firemních údajů podle IČO.
*   **Správa hesel:**
    *   **Změna hesla:** Ověření starého hesla, kontrola shody nových hesel.
    *   **Zapomenuté heslo:** Proces žádosti (generování tokenu, odeslání e-mailu) a potvrzení nového hesla s validním tokenem.
    *   **Oprávnění:** Blokování změny hesla pro uživatele přihlášené přes STAG.
*   **Profil:**
    *   Aktualizace profilu studenta (včetně validace JSON pole `skills`).
    *   Nahrávání souborů (CV ve formátu `.pdf`).
    *   Aktualizace základních údajů firemního uživatele.

#### **Nabídky praxí (`practices`)**
*   **Životní cyklus:** Vytvoření, editace a smazání nabídky.
*   **Validace:** Kontrola logiky dat (např. datum "do" nesmí být před datem "od").
*   **Oprávnění:** Ověření, že student nemůže mazat/upravovat nabídky a firma nemůže zasahovat do nabídek jiných firem.
*   **Filtrování:** Testy pro API endpointy vracející filtrovaná data.

#### **Přihlášky a Pozvánky (`student_practices`)**
*   **Životní cyklus přihlášky:**
    *   Podání přihlášky studentem.
    *   Schvalovací proces (změna stavu z `PENDING` na `APPROVED`).
    *   Sledování průběhu praxe (změna stavu na `IN_PROGRESS` a `COMPLETED`).
*   **Pozvánky od firem:**
    *   Vytvoření pozvánky pro konkrétní studenty.
    *   Akceptace pozvánky studentem (automaticky vytvoří schválenou praxi).
    *   Zamítnutí pozvánky studentem.
    *   Oprávnění: Student nemůže manipulovat s cizími pozvánkami.
*   **Dokumenty:**
    *   Automatické přiřazení výchozích dokumentů (Smlouva, Hodnocení) po schválení praxe.
    *   Testy pro API endpointy na nahrávání a stahování dokumentů.

#### **Organizační struktura (`department`, `subject`)**
*   API endpointy pro výpis studentů a profesorů v rámci jedné katedry.
*   Kontrola oprávnění pro přístup k těmto seznamům.

---

### **2. Frontend (React)**
Celkem **38 testů**, které ověřují komponenty a celé uživatelské scénáře.

#### **Jednotkové testy komponent (Unit Tests)**
*   **`TextField`:** Zobrazení, zápis, validace a přepínání viditelnosti hesla.
*   **`NabidkaForm`:** Zobrazení polí, validace a odesílání formuláře.
*   **`StudentApplicationCard`:** Správné zobrazení stavů přihlášky (barva, text) a dat.

#### **Integrační testy stránek (Integration Tests)**
*   **`LoginPage`:**
    *   Přepínání mezi STAG a firemním přihlášením.
    *   Zpracování STAG ticketu z URL.
    *   Zobrazení chybových hlášek z API.
*   **`RegistracePage`:** Scénář úspěšné registrace firmy a následného automatického přihlášení.
*   **`NabidkaPage` (Výpis nabídek):**
    *   Načtení a zobrazení seznamu praxí.
    *   Inicializace filtrů (načtení lokalit, oborů).
    *   Zobrazení prázdného stavu, pokud nejsou žádné nabídky.
*   **`NabidkaDetailPage` (Detail nabídky):**
    *   Zobrazení všech detailů praxe.
    *   Podmíněné zobrazení tlačítek podle role uživatele (Student vs. Firma).
    *   Kompletní scénář podání přihlášky včetně zobrazení potvrzovacího okna.
*   **`VytvoritNabidku`:**
    *   Načtení potřebných dat (předměty, uživatelé firmy) při inicializaci stránky.
    *   Ověření, že se automaticky dopočítává datum konce praxe.
*   **`ProfilPage`:**
    *   Načtení a zobrazení vlastního i cizího profilu.
    *   Přepnutí do editačního režimu (`?edit=true`).
*   **`StudentApplicationsPage`:** Zobrazení seznamu vlastních přihlášek a pozvánek od firem.

---

### **Jak testy spouštět?**

Testy jsou integrovány do `Makefile` a spouštějí se v Docker kontejnerech, aby bylo zajištěno konzistentní prostředí.

*   **Spuštění backendových testů:**
    ```bash
    make test
    ```
*   **Spuštění frontendových testů:**
    ```bash
    docker container exec internhub-frontend npm test -- --watchAll=false
    ```
