# US-06 — Věcné posouzení obsahu praxe
# Acceptance Criteria:
#   AC-01: Garant vidí přehled všech žádostí čekajících na posouzení.
#   AC-02: Garant může schválit nebo zamítnout žádost jedním kliknutím.
#   AC-03: Při zamítnutí je povinné zadat textový důvod (UC-06a).
#   AC-04: Student je notifikován o výsledku posouzení včetně případného důvodu zamítnutí.
#   AC-05: Systém zaznamenává identitu garanta a čas rozhodnutí.
Feature: Věcné posouzení obsahu praxe garantem
  Jako garant předmětu
  Chci schvalovat nebo zamítat odbornou náplň praxí
  Abych zajistil soulad se studijním programem

  Background:
    Given jsem přihlášen jako garant
    And existuje alespoň jedna žádost ve stavu "Čeká na schválení obsahu"

  # AC-01, AC-02, AC-05 | UAT: TC-06-01
  Scenario: Schválení žádosti o praxi
    When otevřu přehled žádostí čekajících na posouzení
    And vyberu konkrétní žádost
    And kliknu na "Schválit"
    Then žádost se přepne do stavu "Obsah praxe schválen"
    And student obdrží notifikaci o schválení
    And systém zaznamená mou identitu a čas rozhodnutí

  # AC-02, AC-04 | UAT: TC-06-02
  Scenario: Zamítnutí žádosti s povinným důvodem
    When vyberu žádost a kliknu na "Zamítnout"
    Then systém zobrazí povinné pole "Důvod zamítnutí"
    When vyplním důvod a potvrdím
    Then žádost se přepne do stavu "Zamítnutí obsahu"
    And student obdrží notifikaci včetně důvodu zamítnutí

  # AC-03 | UAT: TC-06-03
  Scenario: Pokus zamítnout žádost bez zadání důvodu
    When kliknu na "Zamítnout" a nechám důvod prázdný
    And kliknu na "Potvrdit"
    Then systém zobrazí chybu "Důvod zamítnutí je povinný"
    And žádost zůstane ve stavu "Čeká na schválení obsahu"
