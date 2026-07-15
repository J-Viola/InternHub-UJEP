# US-08 — Správa smluvních stavů
# Acceptance Criteria:
#   AC-01: Garant vidí seznam praxí ve stavu ČEKÁ_NA_SMLOUVU.
#   AC-02: Potvrzení je možné provést pouze po fyzickém shromáždění dokumentu.
#   AC-03: Po potvrzení je praxe přepnuta do stavu Zasmluvněno.
#   AC-04: Systém umožňuje zaznamenat datum fyzického přijetí smlouvy.
#   AC-05: Pokud smlouva nedorazí do definovaného termínu, systém eskaluje upozornění.
Feature: Správa smluvních stavů praxe
  Jako garant předmětu
  Chci manuálně potvrdit přijetí podepsané smlouvy
  Abych zajistil evidenci smluvní dokumentace

  Background:
    Given jsem přihlášen jako garant
    And existuje praxe ve stavu "Čeká na zasmluvnění"

  # AC-01, AC-02, AC-03, AC-04 | UAT: TC-08-01
  Scenario: Úspěšné potvrzení přijetí smlouvy
    When otevřu seznam praxí čekajících na smlouvu
    And vyberu konkrétní praxi
    And zadám datum fyzického přijetí smlouvy
    And kliknu na "Potvrdit přijetí smlouvy"
    Then praxe se přepne do stavu "Zasmluvněno"
    And datum potvrzení je uloženo v systému

  # AC-05 | UAT: TC-08-02
  Scenario: Eskalace při nedodání smlouvy v termínu
    Given termín pro dodání smlouvy uplynul
    And praxe je stále ve stavu "Čeká na zasmluvnění"
    Then systém automaticky přiřadí praxi příznak "SMLOUVA_PO_TERMINU"
    And garant obdrží eskalační upozornění
