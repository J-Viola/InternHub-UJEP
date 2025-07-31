Feature: Vytvoření nabídky praxe

  Scenario: Firma vytvoří novou nabídku
    Given firma je přihlášená
    When klikne na "Nová nabídka"
    And vyplní formulář
    And klikne na "Vytvořit"
    Then se nabídka uloží a je viditelná studentům
