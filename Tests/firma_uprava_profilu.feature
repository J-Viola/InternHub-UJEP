Feature: Úprava profilu firmy

  Scenario: Firma upraví svůj profil
    Given firma je přihlášená
    When přejde do sekce "Účet organizace"
    And provede úpravy
    Then se změny uloží
