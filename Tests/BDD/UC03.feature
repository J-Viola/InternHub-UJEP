# US-03 — Sledování stavu schválení
# Acceptance Criteria:
#   AC-01: Student vidí aktuální stav žádosti (např. Čeká na schválení obsahu, Čeká na zasmluvnění, Přihláška na praxi odmítnuta, Zasmluvněno).
#   AC-02: Systém zobrazuje historii změn stavů s časovými razítky.
#   AC-03: Při změně stavu obdrží student notifikaci (e-mail / in-app).
#   AC-04: V případě zamítnutí je zobrazen důvod zamítnutí zadaný garantem.
Feature: Sledování stavu žádosti o praxi
  Jako student
  Chci sledovat aktuální stav životního cyklu své žádosti
  Abych věděl, co se děje a co se ode mě očekává

  Background:
    Given jsem přihlášen jako student
    And mám podanou alespoň jednu žádost o praxi

  # AC-01 | UAT: TC-03-01
  Scenario: Zobrazení aktuálního stavu žádosti
    When otevřu přehled svých žádostí
    Then vidím aktuální stav každé žádosti
    And stav je jeden z: "Čeká na schválení garanta", "Čeká na schválení organizací", "Čeká na schválení obsahu", "Obsah praxe schválen", "Čeká na zasmluvnění", "Zasmluvněno", "Zahájeno", "Ukončeno", "Splněno", "Přihláška na praxi odmítnuta", "Stornováno"

  # AC-02 | UAT: TC-03-02
  Scenario: Zobrazení historie změn stavů
    When kliknu na detail konkrétní žádosti
    Then vidím chronologický seznam změn stavů s časovými razítky

  # AC-03 | UAT: TC-03-03
  Scenario: Notifikace při změně stavu
    Given moje žádost je ve stavu "Čeká na schválení obsahu"
    When garant moji žádost schválí
    Then obdržím notifikaci o změně stavu
    And stav žádosti se aktualizuje na "Obsah praxe schválen"

  # AC-04 | UAT: TC-03-04
  Scenario: Zobrazení důvodu zamítnutí
    Given moje žádost byla zamítnuta garantem
    When otevřu detail žádosti
    Then vidím důvod zamítnutí zadaný garantem
    And stav je zobrazen jako "Přihláška na praxi odmítnuta"
