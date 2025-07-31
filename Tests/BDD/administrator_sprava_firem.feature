Feature: Správa firem

  Scenario: Administrátor přidá nového firemního uživatele
    Given administrátor je přihlášen
    When klikne na "Založit účet"
    And vyplní údaje
    Then se vytvoří nový účet

  Scenario: Administrátor upraví údaje uživatele
    Given administrátor je přihlášen
    When vybere uživatele a klikne na "Upravit"
    And vyplní údaje a klikne Uložit
    Then provede změny a uloží je
