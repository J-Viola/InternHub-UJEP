# US-07 — Administrace alokace
# Acceptance Criteria:
#   AC-01: Před potvrzením alokace systém automaticky ověří volnou kapacitu partnera (UC-07a).
#   AC-02: Pokud kapacita není dostupná, systém blokuje potvrzení a zobrazí upozornění.
#   AC-03: Garant vidí aktuální obsazenost kapacity u každého inzerátu.
#   AC-04: Po potvrzení alokace jsou student i organizace notifikováni.
Feature: Administrace alokace studentů k inzerátům
  Jako garant předmětu
  Chci schvalovat přiřazení studentů a kontrolovat kapacity
  Abych zajistil korektní alokaci bez překročení limitů

  Background:
    Given jsem přihlášen jako garant
    And existuje inzerát s kapacitou 2 místa, obsazena 1

  # AC-01, AC-04 | UAT: TC-07-01
  Scenario: Úspěšná alokace studenta s volnou kapacitou
    When schválím přiřazení studenta k inzerátu
    Then systém ověří dostupnou kapacitu
    And kapacita je volná
    And praxe přejde do stavu "Čeká na schválení organizací"
    And student i organizace obdrží notifikaci

  # AC-02 | UAT: TC-07-02
  Scenario: Pokus o alokaci při plné kapacitě
    Given kapacita inzerátu je plně obsazena
    When se pokusím schválit přiřazení dalšího studenta
    Then systém zablokuje potvrzení
    And zobrazí upozornění "Kapacita partnera je plně obsazena"
    And alokace není provedena

  # AC-03 | UAT: TC-07-03
  Scenario: Zobrazení aktuální obsazenosti kapacity
    When otevřu detail inzerátu
    Then vidím aktuální obsazenost ve formátu "obsazeno/celkem" (napr. "1/2")
