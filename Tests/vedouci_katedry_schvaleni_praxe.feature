Feature: Kontrola dokumentů

  Scenario: Vedoucí katedry zkontroluje dokumenty
    Given vedoucí je přihlášen
    When přejde na stránku "Správa stáží"
    And klikne na Schválit"
    And potvrdí volbu
    Then se schválí nová praxe
