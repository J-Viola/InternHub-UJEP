Feature: Úprava nebo smazání nabídky

  Scenario: Firma upraví existující nabídku
    Given firma je přihlášená
    And má existující nabídku
    When klikne na "Upravit"
    And provede změny
    And klikne na "Uložit"
    Then se nabídka aktualizuje

  Scenario: Firma smaže nabídku
    Given firma je přihlášená
    When klikne na "Zneaktivnit"
    Then je nabídka odstraněna ze systému
