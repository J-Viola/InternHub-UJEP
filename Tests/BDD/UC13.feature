# UC-13 — Standardní životní cyklus praxe (stavový automat)
# Acceptance Criteria (stavový automat):
#   AC-LC-01: Po přihlášce z katalogu je praxe ve stavu „Čeká na schválení garanta“.
#   AC-LC-02: Po schválení garantem přechází praxe do stavu „Čeká na schválení organizací“.
#   AC-LC-03: Zamítnutí garantem nebo organizací vede do stavu „Přihláška na praxi odmítnuta“.
#   AC-LC-04: Po schválení organizací přechází praxe do stavu „Čeká na zasmluvnění“.
#   AC-LC-04b: Po nahrání smluvních dokumentů studentem přechází praxe do stavu „Čeká na schválení dokumentů“.
#   AC-LC-05: Po schválení smluvních dokumentů garantem přechází praxe do stavu „Zasmluvněno“.
#   AC-LC-06: Po datu zahájení přechází praxe do stavu „Zahájeno“, po uplynutí období do „Ukončeno“.
#   AC-LC-07: Po schválení závěrečné dokumentace přechází praxe do stavu „Splněno“.
#   AC-LC-08: Zamítnuté dokumenty vedou do stavu „Dokumenty zamítnuty“ s možností nápravy.
#   AC-LC-09: Z aktivního stavu lze proces ukončit přechodem do stavu „Stornováno“.
Feature: Standardní životní cyklus praxe
  Jako systém InternHub
  Chci vynucovat stavový automat standardní praxe
  Abych zabránil neoprávněným operacím mimo aktuální fázi procesu

  Background:
    Given student je přihlášen v systému InternHub
    And existuje schválený inzerát organizace ve stavu "Aktivní"

  # AC-LC-01 | UAT: TC-13-01
  Scenario: Přihláška studenta z katalogu
    When student vybere inzerát a odešle přihlášku
    Then praxe je uložena ve stavu "Čeká na schválení garanta"

  # AC-LC-02 | UAT: TC-13-02
  Scenario: Schválení přihlášky garantem
    Given existuje praxe ve stavu "Čeká na schválení garanta"
    When garant schválí přihlášku studenta
    Then praxe se přepne do stavu "Čeká na schválení organizací"

  # AC-LC-03 | UAT: TC-13-03
  Scenario: Zamítnutí přihlášky garantem
    Given existuje praxe ve stavu "Čeká na schválení garanta"
    When garant zamítne přihlášku s uvedením důvodu
    Then praxe se přepne do stavu "Přihláška na praxi odmítnuta"

  # AC-LC-04 | UAT: TC-13-04
  Scenario: Schválení přihlášky organizací
    Given existuje praxe ve stavu "Čeká na schválení organizací"
    When organizace schválí přihlášku studenta
    Then praxe se přepne do stavu "Čeká na zasmluvnění"

  # AC-LC-03 | UAT: TC-13-05
  Scenario: Zamítnutí přihlášky organizací
    Given existuje praxe ve stavu "Čeká na schválení organizací"
    When organizace zamítne přihlášku s uvedením důvodu
    Then praxe se přepne do stavu "Přihláška na praxi odmítnuta"

  # AC-LC-04b | UAT: TC-13-06
  Scenario: Nahrání smluvních dokumentů studentem
    Given existuje praxe ve stavu "Čeká na zasmluvnění"
    When student nahraje smluvní dokumenty
    Then praxe se přepne do stavu "Čeká na schválení dokumentů"

  # AC-LC-05 | UAT: TC-13-07
  Scenario: Schválení smluvních dokumentů garantem
    Given existuje praxe ve stavu "Čeká na schválení dokumentů"
    And student nahrál smluvní dokumenty
    When garant schválí nahrané dokumenty
    Then praxe se přepne do stavu "Zasmluvněno"

  # AC-LC-08 | UAT: TC-13-08
  Scenario: Zamítnutí smluvních dokumentů
    Given existuje praxe ve stavu "Čeká na schválení dokumentů"
    When garant zamítne nahrané dokumenty
    Then praxe se přepne do stavu "Dokumenty zamítnuty"

  # AC-LC-06 | UAT: TC-13-09
  Scenario: Přechod do stavu Zahájeno a Ukončeno
    Given existuje praxe ve stavu "Zasmluvněno"
    When nastane plánované datum zahájení praxe
    Then praxe se přepne do stavu "Zahájeno"
    When uplyne stanovený časový rámec praxe
    Then praxe se přepne do stavu "Ukončeno"

  # AC-LC-07 | UAT: TC-13-10
  Scenario: Splnění praxe po schválení závěrečné dokumentace
    Given existuje praxe ve stavu "Ukončeno"
    And student nahrál závěrečnou dokumentaci
    When garant schválí závěrečné dokumenty
    Then praxe se přepne do stavu "Splněno"

  # AC-LC-09 | UAT: TC-13-11
  Scenario: Storno aktivní praxe
    Given existuje praxe ve stavu "Zasmluvněno"
    When student podá žádost o storno s uvedením důvodu
    Then praxe se přepne do stavu "Stornováno"
