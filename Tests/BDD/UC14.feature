# UC-14 — Životní cyklus inzerce (stavový automat)
# Acceptance Criteria:
#   AC-LI-01: Nový inzerát je uložen ve stavu „Čeká na schválení obsahu“.
#   AC-LI-02: Po schválení garantem přechází inzerát do stavu „Aktivní“.
#   AC-LI-03: Zamítnutí obsahu vede do stavu „Zamítnutí obsahu“ s možností úpravy.
#   AC-LI-04: Po datu zahájení nebo naplnění kapacity přechází inzerát do stavu „Uzavřeno“.
Feature: Životní cyklus inzerce
  Jako systém InternHub
  Chci vynucovat stavový automat inzerátu
  Abych zajistil kontrolu obsahu publikovaných nabídek

  Background:
    Given zástupce organizace je přihlášen v systému InternHub

  # AC-LI-01 | UAT: TC-14-01
  Scenario: Vytvoření inzerátu čekajícího na schválení
    When vytvoří a publikuje nový inzerát
    Then inzerát je uložen ve stavu "Čeká na schválení obsahu"

  # AC-LI-02 | UAT: TC-14-02
  Scenario: Schválení inzerátu garantem
    Given existuje inzerát ve stavu "Čeká na schválení obsahu"
    When garant schválí obsah inzerátu
    Then inzerát se přepne do stavu "Aktivní"

  # AC-LI-03 | UAT: TC-14-03
  Scenario: Zamítnutí inzerátu a návrat k úpravě
    Given existuje inzerát ve stavu "Čeká na schválení obsahu"
    When garant zamítne obsah inzerátu
    Then inzerát se přepne do stavu "Zamítnutí obsahu"
    When organizace upraví parametry inzerátu
    Then inzerát se vrátí do stavu "Čeká na schválení obsahu"

  # AC-LI-04 | UAT: TC-14-04
  Scenario: Automatické uzavření inzerátu po datu zahájení
    Given existuje inzerát ve stavu "Aktivní"
    When nastane plánované datum zahájení praxe
    Then inzerát se přepne do stavu "Uzavřeno"
