# UC-15 — Individuální (manuální) životní cyklus praxe (stavový automat)
# Acceptance Criteria:
#   AC-LM-01: Po odeslání individuální žádosti je praxe ve stavu „Čeká na schválení obsahu“.
#   AC-LM-02: Po schválení obsahu garantem přechází praxe do stavu „Obsah praxe schválen“.
#   AC-LM-03: Zamítnutí obsahu vede do stavu „Zamítnutí obsahu“ s možností úpravy parametrů.
#   AC-LM-04: Po fyzickém doručení smluv přechází praxe do stavu „Zasmluvněno“.
#   AC-LM-05: Realizační fáze probíhá přes stavy „Zahájeno“ a „Ukončeno“ (shodně se standardním cyklem).
#   AC-LM-06: Po schválení závěrečné dokumentace přechází praxe do stavu „Splněno“.
#   AC-LM-07: Zamítnuté závěrečné dokumenty vedou do stavu „Dokumenty zamítnuty“ s možností nápravy.
Feature: Individuální (manuální) životní cyklus praxe
  Jako systém InternHub
  Chci vynucovat stavový automat individuální praxe
  Abych zajistil správný postup studentů mimo nabídkový katalog

  Background:
    Given student je přihlášen v systému InternHub

  # AC-LM-01 | UAT: TC-15-01
  Scenario: Odeslání formuláře individuální praxe
    When student vyplní a odešle formulář individuální praxe
    Then praxe je uložena ve stavu "Čeká na schválení obsahu"

  # AC-LM-02 | UAT: TC-15-02
  Scenario: Schválení obsahu garantem
    Given existuje individuální praxe ve stavu "Čeká na schválení obsahu"
    When garant schválí obsah praxe
    Then praxe se přepne do stavu "Obsah praxe schválen"

  # AC-LM-03 | UAT: TC-15-03
  Scenario: Zamítnutí obsahu a návrat k úpravě
    Given existuje individuální praxe ve stavu "Čeká na schválení obsahu"
    When garant zamítne obsah praxe s uvedením důvodu
    Then praxe se přepne do stavu "Zamítnutí obsahu"
    When student upraví parametry praxe
    Then praxe se vrátí do stavu "Čeká na schválení obsahu"

  # AC-LM-04 | UAT: TC-15-04
  Scenario: Potvrzení fyzického doručení smluv
    Given existuje individuální praxe ve stavu "Obsah praxe schválen"
    When garant potvrdí fyzické doručení smluv
    Then praxe se přepne do stavu "Zasmluvněno"

  # AC-LM-05 | UAT: TC-15-05
  Scenario: Realizační fáze individuální praxe
    Given existuje individuální praxe ve stavu "Zasmluvněno"
    When nastane plánované datum zahájení praxe
    Then praxe se přepne do stavu "Zahájeno"
    When uplyne stanovený časový rámec praxe
    Then praxe se přepne do stavu "Ukončeno"

  # AC-LM-06 | UAT: TC-15-06
  Scenario: Splnění individuální praxe
    Given existuje individuální praxe ve stavu "Ukončeno"
    And student nahrál závěrečnou dokumentaci
    When garant schválí závěrečné dokumenty
    Then praxe se přepne do stavu "Splněno"

  # AC-LM-07 | UAT: TC-15-07
  Scenario: Zamítnutí závěrečných dokumentů u individuální praxe
    Given existuje individuální praxe ve stavu "Ukončeno"
    When garant zamítne nahrané závěrečné dokumenty
    Then praxe se přepne do stavu "Dokumenty zamítnuty"
    When student nahraje opravené dokumenty
    Then praxe se vrátí do stavu "Ukončeno"
