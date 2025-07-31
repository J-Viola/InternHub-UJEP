Feature: Zobrazení studentů přihlášených na praxi

  Scenario: Vedoucí katedry si zobrazí přihlášené studenty na praxi
    Given vedoucí je přihlášen
    When přejde na stránku "Nabídka praxí"
    And klikne na "Přihlášení studenti"
    Then se zobrazí přihlášení studenti na praxi
