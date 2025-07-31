Feature: Odeslání přihlášky na praxi

  Scenario: Student odešle přihlášnu na praxi
    Given student je přihlášen do systému
    And vybral si konkrétní nabídku
    When klikne na "Podat přihlášku"
    Then se přihláška odešle firmě
