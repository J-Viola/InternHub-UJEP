# US-01 — Vyhledání praxe
# Acceptance Criteria:
#   AC-01: Student může filtrovat nabídky podle oboru, lokality, délky trvání a kapacity.
#   AC-02: Výsledky se aktualizují dynamicky bez nutnosti obnovení stránky.
#   AC-03: Pokud filtr nevrátí žádné výsledky, systém zobrazí informativní hlášku.
#   AC-04: Student může uložit svůj výběr a přihlásit se na praxi přímo z katalogu.
Feature: Vyhledání praxe v katalogu
  Jako student
  Chci vyhledávat nabídky praxí s pomocí filtrů
  Abych rychle našel vhodnou praxi pro svůj obor

  Background:
    Given jsem přihlášen jako student
    And katalog obsahuje alespoň 10 nabídek praxí

  # AC-01, AC-02 | UAT: TC-01-01
  Scenario: Úspěšné vyhledání praxe s filtry
    When otevřu katalog praxí
    And nastavím filtr "obor" na "Informatika"
    And nastavím filtr "lokalita" na "Ústí nad Labem"
    Then vidím pouze nabídky odpovídající nastaveným filtrům
    And výsledky se zobrazí bez obnovení stránky

  # AC-03 | UAT: TC-01-02
  Scenario: Filtr nevrátí žádné výsledky
    When nastavím filtr "obor" na "Neexistující obor"
    Then systém zobrazí zprávu "Žádné nabídky neodpovídají zadaným filtrům"
    And stránka nezobrazuje žádnou nabídku praxe

  # AC-04 | UAT: TC-01-03
  Scenario: Přihlášení na praxi z katalogu
    When vyberu konkrétní nabídku praxe
    And kliknu na "Přihlásit se"
    Then systém uloží moji žádost
    And praxe je uložena ve stavu "Čeká na schválení garanta"
    And zobrazí potvrzení "Žádost byla úspěšně odeslána"
