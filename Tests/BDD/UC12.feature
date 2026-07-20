# US-12 — Evaluace studenta
# Acceptance Criteria:
#   AC-01: Mentor má přístup k hodnotícímu formuláři po přepnutí praxe do stavu Ukončeno.
#   AC-02: Formulář obsahuje strukturované hodnotící kategorie (dle definice školy).
#   AC-03: Nahrání naskenovaného a podepsaného hodnotícího archu je povinné (UC-12a).
#   AC-04: Systém akceptuje pouze soubory PDF s max. velikostí dle konfigurace.
#   AC-05: Po úspěšném odeslání je garant notifikován o dokončené evaluaci.
#   AC-06: Evaluaci nelze odeslat bez nahraného dokumentu.
Feature: Evaluace studenta mentorem po ukončení praxe
  Jako mentor z externí organizace
  Chci vyplnit hodnotící formulář a nahrát podepsaný evaluační arch
  Abych formálně uzavřel praxi se svým hodnocením

  Background:
    Given jsem přihlášen jako mentor
    And existuje praxe ve stavu "Ukončeno" přiřazená mé organizaci

  # AC-01, AC-02, AC-05 | UAT: TC-12-01
  Scenario: Úspěšná evaluace studenta s nahráním dokumentu
    When otevřu formulář evaluace pro danou praxi
    And vyplním všechny hodnotící kategorie
    And nahraji soubor "hodnoceni_podepsane.pdf"
    And kliknu na "Odeslat evaluaci"
    Then evaluace je uložena v systému
    And garant obdrží notifikaci o dokončené evaluaci

  # AC-03, AC-06 | UAT: TC-12-02
  Scenario: Pokus odeslat evaluaci bez nahraného dokumentu
    When vyplním hodnotící formulář
    And kliknu na "Odeslat evaluaci" bez nahrání souboru
    Then systém zobrazí chybu "Nahrání podepsaného hodnotícího archu je povinné"
    And evaluace není odeslána

  # AC-04 | UAT: TC-12-03
  Scenario: Pokus nahrát dokument v nepovoleném formátu
    Given mám otevřený hodnotící formulář
    When nahraji soubor "hodnoceni.docx"
    Then systém zobrazí chybu "Povolený formát je pouze PDF"
    And soubor není přijat

  # AC-01 (negativní) | UAT: TC-12-04
  Scenario: Nedostupnost formuláře před ukončením praxe
    Given praxe je ve stavu "Zasmluvněno"
    When se pokusím otevřít formulář evaluace
    Then systém zobrazí zprávu "Evaluace je dostupná až po ukončení praxe"
