Feature: Prohlížení nabídek praxí

  Scenario: Student zobrazí seznam dostupných praxí
    Given student je přihlášen do systému
    When přejde na stránku s nabídkami praxí
    Then se zobrazí seznam aktuálně dostupných praxí
