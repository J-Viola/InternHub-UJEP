Feature: Stažení návrhu smlouvy

  Scenario: Student stáhne návrh smlouvy
    Given student má zapsaný kurz odborné praxe
    When přejde na stránku "Praxe"
    And klikne na "Stáhnout"
    Then se vygeneruje a stáhne PDF dokument
