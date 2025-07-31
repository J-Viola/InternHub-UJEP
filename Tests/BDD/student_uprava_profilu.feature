Feature: Úprava profilu studenta

  Scenario: Student upraví svůj profil
    Given student je přihlášen
    When přejde do uživatelského profilu
    And klikne na "Upravit údaje"
    And provede úpravy
    And klikne na "Uložit"
    Then se změny uloží
