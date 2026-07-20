# US-04 — Nahrání dokumentace
# Acceptance Criteria:
#   AC-01: Systém přijímá soubory formátů PDF, DOCX a XLSX.
#   AC-02: Maximální povolená velikost souboru je definována (např. 10 MB).
#   AC-03: Student vidí seznam všech dosud nahraných dokumentů s datumem nahrání.
#   AC-04: Garant je notifikován o nahrání nového dokumentu.
#   AC-05: Nahrání dokumentu mimo stanovený termín je systémem označeno jako pozdní.
Feature: Nahrání průběžné dokumentace praxe
  Jako student
  Chci nahrávat zprávy a výkazy práce do systému
  Abych splnil dokumentační povinnosti

  Background:
    Given jsem přihlášen jako student
    And mám aktivní praxi ve stavu "Zasmluvněno"

  # AC-01, AC-03, AC-04 | UAT: TC-04-01
  Scenario: Úspěšné nahrání dokumentu
    When přejdu na sekci "Dokumentace" své praxe
    And nahraji soubor "zprava_tyden1.pdf" o velikosti 2 MB
    Then systém soubor přijme a zobrazí ho v seznamu dokumentů
    And garant obdrží notifikaci o novém dokumentu

  # AC-01 (negativní) | UAT: TC-04-02
  Scenario: Pokus o nahrání souboru nepovoleného formátu
    When nahraji soubor "zprava.exe"
    Then systém zobrazí chybu "Nepodporovaný formát souboru. Povolené formáty: PDF, DOCX, XLSX"
    And soubor není nahrán

  # AC-02 | UAT: TC-04-03
  Scenario: Pokus o nahrání souboru překračujícího limit
    When nahraji soubor o velikosti 15 MB
    Then systém zobrazí chybu "Soubor překračuje maximální povolenou velikost 10 MB"

  # AC-05 | UAT: TC-04-04
  Scenario: Nahrání dokumentu po termínu
    Given termín odevzdání dokumentace uplynul
    When nahraji dokument
    Then systém dokument přijme
    And označí ho jako "Odevzdáno po termínu"
