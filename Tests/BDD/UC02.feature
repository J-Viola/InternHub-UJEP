# US-02 — Zadání individuální praxe
# Acceptance Criteria:
#   AC-01: Formulář obsahuje pole: název organizace, kontaktní osoba, popis náplně, termín, rozsah hodin.
#   AC-02: Systém validuje povinná pole před odesláním.
#   AC-03: Po odeslání je žádost automaticky postoupena garantovi ke věcnému posouzení (UC-06).
#   AC-04: Student obdrží potvrzení přijetí žádosti.
Feature: Zadání individuálně domluvené praxe s validací přes ARES
  Jako student
  Chci manuálně zadat parametry individuální praxe s využitím registru ARES
  Abych minimalizoval chyby při zadávání údajů o organizaci a doložil odbornost praxe

  Background:
    Given jsem přihlášen jako student

  # RF-03 (Registr ARES) | UAT: Kritické TC-04
  Scenario: Úspěšné vyhledání organizace podle IČO a předvyplnění údajů (ARES)
    When otevřu formulář "Zadat individuální praxi"
    And zadám platné IČO "44555601"
    And kliknu na "Vyhledat v registru ARES"
    Then systém ověří subjekt v registru ARES
    And předvyplní pole "Název organizace" a "Sídlo" oficiálními údaji
    And uzamkne tato pole pro ruční editaci

  # RF-03 (Registr ARES) | UAT: Kritické TC-04, TC-06
  Scenario: Zadání neexistujícího nebo neplatného IČO
    When otevřu formulář "Zadat individuální praxi"
    And zadám neplatné IČO "00000000"
    And kliknu na "Vyhledat v registru ARES"
    Then systém zobrazí chybovou zprávu "Subjekt s tímto IČO nebyl v registru ARES nalezen"
    And pole "Název organizace" zůstane prázdné a neuzamčené
    And systém neumožní odeslat formulář bez vyplnění povinných polí

  # AC-01, AC-03, AC-04 | UAT: TC-02-03
  Scenario: Úspěšné odeslání žádosti s doloženou dokumentací
    When otevřu formulář "Zadat individuální praxi"
    And mám vyhledanou organizaci z registru ARES
    And vyplním pole "Kontaktní osoba", "Popis náplně", "Termín" a "Rozsah hodin"
    And nahraji soubor "detaily_praxe.pdf" s popisem odbornosti
    And kliknu na "Odeslat ke schválení"
    Then systém ověří formát přílohy
    And uloží žádost ve stavu "Čeká na schválení obsahu"
    And garant obdrží notifikaci o nové žádosti

  # AC-02 | UAT: TC-02-04
  Scenario: Pokus o odeslání žádosti bez nahrané dokumentace
    When otevřu formulář "Zadat individuální praxi"
    And mám vyhledanou organizaci z registru ARES
    And vyplním textová pole formuláře
    But nenahraji soubor s detaily praxe
    And kliknu na "Odeslat ke schválení"
    Then systém zablokuje odeslání
    And zobrazí chybu "Nahrání dokumentu s detaily praxe je povinné"
