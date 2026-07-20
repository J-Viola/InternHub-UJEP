# US-11 — Inzerce nabídky praxe
# Acceptance Criteria:
#   AC-01: Formulář obsahuje pole: název pozice, popis náplně, počet míst, termín, kontaktní osoba.
#   AC-02: Inzerát je po vytvoření automaticky odeslán garantovi ke věcnému posouzení.
#   AC-03: Organizace vidí stav svého inzerátu (čeká na schválení / aktivní / zamítnuto).
#   AC-04: Organizace může inzerát editovat, dokud není ve stavu Aktivní.
Feature: Inzerce nabídky praxe organizací
  Jako zástupce externí organizace
  Chci vytvořit inzerát s popisem praxe
  Abych oslovil vhodné studenty

  Background:
    Given jsem přihlášen jako zástupce organizace

  # AC-01, AC-02 | UAT: TC-11-01
  Scenario: Úspěšné vytvoření inzerátu
    When otevřu formulář "Nový inzerát"
    And vyplním pole "Název pozice" hodnotou "Junior Developer"
    And vyplním pole "Popis náplně", "Počet míst", "Termín" a "Kontaktní osoba"
    And kliknu na "Publikovat inzerát"
    Then inzerát je uložen ve stavu "Čeká na schválení obsahu"
    And inzerát se zobrazí v náhledu garanta ke schválení
    And garant obdrží notifikaci o novém inzerátu

  # AC-03 | UAT: TC-11-02
  Scenario: Zobrazení stavu inzerátu
    When otevřu přehled svých inzerátů
    Then vidím aktuální stav každého inzerátu

  # AC-04 | UAT: TC-11-03
  Scenario: Editace inzerátu před schválením
    Given inzerát je ve stavu "Čeká na schválení obsahu"
    When kliknu na "Upravit inzerát"
    Then mohu editovat obsah inzerátu
    And uložit změny

  # AC-04 (negativní) | UAT: TC-11-04
  Scenario: Blokace editace schváleného inzerátu
    Given inzerát je ve stavu "Aktivní"
    When se pokusím kliknout na "Upravit inzerát"
    Then systém zobrazí upozornění "Schválený inzerát nelze editovat"
