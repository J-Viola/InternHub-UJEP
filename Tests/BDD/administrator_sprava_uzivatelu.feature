Feature: Správa uživatelů

  Scenario: Administrátor upraví informace o uživateli
    Given administrátor je přihlášen
    When přejde na seznam uživatelů
    And vybere konkrétního uživatele
    And upraví jeho údaje
    Then se změny uloží

