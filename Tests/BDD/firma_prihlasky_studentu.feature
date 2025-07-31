Feature: Správa přihlášek studentů

  Scenario: Firma zobrazí přijaté žádosti
    Given firma je přihlášená
    When přejde do sekce "Přihlášení studenti"
    Then se zobrazí seznam studentů

  Scenario: Firma schválí žádost
    Given firma vidí konkrétní žádost
    When klikne na "Schválit"
    Then je přihláška schválená
